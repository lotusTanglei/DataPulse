import { expect, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import type { ScreenAssetResponse } from "@datapulse/schema";
import { apiGet, apiPatch, apiPost, appOrigin, authenticate, createPublishedScreen, generateDisplayKey, issueEmbedTicket, mutationHeaders, rotateEmbedApiKey, type ScreenRecord } from "./helpers.js";
import { loadRuntimeConfig } from "./runtime-config.js";

function broadcastDocument() {
  return {
    canvas: { width: 960, height: 540, background: { color: "#f3f5f7" } },
    parameters: [{ id: "region", name: "region", data_type: "string", default: "华东", mutable: true }],
    theme: { id: "datapulse-light", tokens: {
      text_primary: "#17242c", text_secondary: "#465965", panel_background: "#ffffff",
      panel_background_alt: "#edf2f4", panel_border: "#87949e", accent: "#008478",
    } },
    components: [
      {
        id: "kpi", type: "builtin.kpi", frame: { x: 40, y: 70, width: 320, height: 180 },
        props: { label: "本月销售额" },
        data_binding: { source: "static", static_data: { columns: [{ name: "amount", data_type: "number" }], rows: [[1234]] } },
      },
      {
        id: "speaker", type: "builtin.digital_human", frame: { x: 470, y: 30, width: 420, height: 480 },
        style: { background_color: "#ffffff", border_width: 1, border_color: "#87949e", border_radius: 4 },
        props: { name: "运营播报员", role: "数据播报", speech_template: "本月销售额 {{sales.value | number}} 元。", muted: true, subtitle_font_size: 22 },
        data_binding: { source: "components", variables: [{ name: "sales.value", component_id: "kpi", field: "amount" }] },
      },
    ],
  };
}

function structuredBroadcastDocument() {
  const document = broadcastDocument();
  Object.assign(document.components[1]!.props, {
    speech_template: "旧模板不应覆盖结构化话术。",
    speech_segments: [
      { kind: "paragraph", text: "结构化开场" },
      { kind: "pause", duration_ms: 700 },
      { kind: "emphasis", text: "重点播报" },
    ],
  });
  return document;
}

test("digital human publishes, renders shared data and keeps the draft isolated", async ({ page }, info) => {
  await authenticate(page);
  const screen = await createPublishedScreen(page, "数字人发布 " + Date.now(), broadcastDocument());
  const key = await generateDisplayKey(page, screen.id);
  await page.goto("/play/" + screen.id + "?key=" + encodeURIComponent(key));
  const speaker = page.locator('[data-component-id="speaker"]');
  await expect(speaker.locator(".digital-human__subtitle")).toHaveText("本月销售额 1,234 元。");
  await expect(speaker.locator(".digital-human")).toHaveAttribute("data-status", "muted");
  await expect(speaker.locator('[role="region"]')).toHaveAttribute("aria-labelledby", "digital-human-speaker-name");
  await expect(speaker.locator(".digital-human__subtitle")).toHaveAttribute("tabindex", "0");
  await speaker.locator(".digital-human__subtitle").focus();
  await expect(speaker.locator(".digital-human__subtitle")).toBeFocused();
  await expect(speaker.locator(".digital-human__identity")).toHaveCSS("color", "rgb(23, 36, 44)");
  const captions = speaker.locator(".digital-human__captions");
  await expect(captions).toHaveCSS("white-space", "nowrap");
  await expect(captions.locator("input")).toHaveCSS("min-height", "0px");
  await expect(page).toHaveURL(new RegExp("/play/" + screen.id + "$"));
  const desktop = info.outputPath("digital-human-desktop.png");
  await page.screenshot({ path: desktop });
  await info.attach("digital-human-desktop", { path: desktop, contentType: "image/png" });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(speaker.locator(".digital-human__subtitle")).toBeVisible();
  const mobile = info.outputPath("digital-human-mobile.png");
  await page.screenshot({ path: mobile });
  await info.attach("digital-human-mobile", { path: mobile, contentType: "image/png" });
  await expect(page.locator(".screen-runtime")).toBeVisible();

  await page.setViewportSize({ width: 3840, height: 2160 });
  await page.goto("/play/" + screen.id);
  await expect(speaker.locator(".digital-human")).toBeVisible();
  await expect.poll(() => speaker.locator(".digital-human").evaluate((node) => ({
    overflow: node.scrollWidth > node.clientWidth || node.scrollHeight > node.clientHeight,
    subtitleSize: Number.parseFloat(getComputedStyle(node.querySelector(".digital-human__subtitle")!).fontSize),
  }))).toEqual({ overflow: false, subtitleSize: 22 });

  const changed = broadcastDocument();
  changed.components[1]!.props.speech_template = "草稿未发布";
  await apiPatch(page, "/api/admin/screens/" + screen.id, { draft_document: changed, expected_revision: screen.draft_revision });
  await page.reload();
  await expect(speaker.locator(".digital-human__subtitle")).toHaveText("本月销售额 1,234 元。");
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/studio/screens/" + screen.id + "/edit");
  await page.locator('[data-canvas-component="speaker"]').click({ position: { x: 20, y: 120 } });
  await expect(page.locator(".speech-inspector")).toBeVisible();
  await expect(page.locator(".speech-inspector textarea")).toHaveValue("草稿未发布");
  const editor = info.outputPath("digital-human-editor.png");
  await page.screenshot({ path: editor });
  await info.attach("digital-human-editor", { path: editor, contentType: "image/png" });
});

test("structured speech segments persist through editor reload and publish", async ({ page }) => {
  await authenticate(page);
  const created = await apiPost<ScreenRecord>(page, "/api/admin/screens", { name: "结构化话术持久化 " + Date.now() });
  const saved = await apiPatch<ScreenRecord>(page, `/api/admin/screens/${created.id}`, {
    draft_document: structuredBroadcastDocument(),
    expected_revision: created.draft_revision,
  });

  await page.goto(`/studio/screens/${created.id}/edit`);
  await page.locator('[data-canvas-component="speaker"]').click({ position: { x: 20, y: 120 } });
  const script = page.locator(".speech-inspector__script");
  await expect(script).toBeVisible();
  await expect(script.locator(".speech-inspector__script-row")).toHaveCount(3);
  await script.locator('textarea[aria-label="话术段落文本 1"]').fill("编辑后开场");
  await script.locator('textarea[aria-label="话术段落文本 1"]').blur();
  await script.locator('input[aria-label="停顿时长 2"]').fill("900");
  await script.locator('input[aria-label="停顿时长 2"]').blur();
  await page.getByLabel("编辑器工具栏").getByRole("button", { name: "保存", exact: true }).click();
  await expect(page.getByLabel("编辑器工具栏").getByText("已保存")).toBeVisible({ timeout: 10_000 });

  await page.reload();
  await page.locator('[data-canvas-component="speaker"]').click({ position: { x: 20, y: 120 } });
  const reloadedScript = page.locator(".speech-inspector__script");
  await expect(reloadedScript.locator('textarea[aria-label="话术段落文本 1"]')).toHaveValue("编辑后开场");
  await expect(reloadedScript.locator('input[aria-label="停顿时长 2"]')).toHaveValue("900");
  await expect(reloadedScript.locator('textarea[aria-label="话术段落文本 3"]')).toHaveValue("重点播报");

  const current = await apiGet<ScreenRecord>(page, `/api/admin/screens/${created.id}`);
  const props = current.draft_document.components.find((item: { id: string }) => item.id === "speaker")?.props as Record<string, unknown>;
  expect(props.speech_segments).toEqual([
    { kind: "paragraph", text: "编辑后开场", duration_ms: 500 },
    { kind: "pause", text: "", duration_ms: 900 },
    { kind: "emphasis", text: "重点播报", duration_ms: 500 },
  ]);
  const published = await apiPost<ScreenRecord>(page, `/api/admin/screens/${created.id}/publish`, { expected_revision: current.draft_revision });
  expect((published.published_document?.components.find((item: { id: string }) => item.id === "speaker")?.props as Record<string, unknown>).speech_segments).toEqual(props.speech_segments);
  const key = await generateDisplayKey(page, created.id);
  await page.goto(`/play/${created.id}?key=${encodeURIComponent(key)}`);
  await expect(page.locator('[data-component-id="speaker"] .digital-human__subtitle')).toHaveText("编辑后开场\n重点播报");
});

test("fake TTS preview is adopted into a published digital human and plays independently", async ({ page }) => {
  test.skip(!process.env.DATAPULSE_E2E_TTS_BASE_URL, "fake TTS fixture is unavailable");
  await authenticate(page);
  const created = await apiPost<ScreenRecord>(page, "/api/admin/screens", { name: "数字人 TTS 闭环 " + Date.now() });
  const saved = await apiPatch<ScreenRecord>(page, `/api/admin/screens/${created.id}`, {
    draft_document: broadcastDocument(), expected_revision: created.draft_revision,
  });
  const provider = await apiPost<{ id: string }>(page, "/api/admin/digital-human/providers", {
    name: "E2E deterministic fake TTS " + Date.now(), provider_type: "openai_compatible",
    base_url: process.env.DATAPULSE_E2E_TTS_BASE_URL, api_key: process.env.DATAPULSE_E2E_TTS_API_KEY,
    default_voice: "alloy", language: "zh-CN", enabled: true, cost_per_minute: 0, provider_version: "v1",
  });
  await page.goto(`/studio/screens/${created.id}/edit`);
  await page.locator('[data-canvas-component="speaker"]').click({ position: { x: 20, y: 120 } });
  const inspector = page.locator(".speech-inspector__tts");
  await expect(inspector).toBeVisible();
  await inspector.locator("select").selectOption(provider.id);
  await expect(inspector.locator("select")).toHaveValue(provider.id);
  await inspector.getByRole("button", { name: "生成 TTS 试听", exact: true }).click();
  await expect(inspector.locator("audio")).toBeVisible({ timeout: 20_000 });
  await inspector.getByRole("button", { name: "采用此音频到草稿", exact: true }).click();
  await expect(page.getByText("TTS 音频已采用到草稿，发布后才会在线使用。", { exact: true })).toBeVisible();
  let draftSnapshot: ScreenRecord | null = null;
  await expect.poll(async () => {
    const current = await apiGet<ScreenRecord>(page, `/api/admin/screens/${created.id}`);
    draftSnapshot = current;
    const props = current.draft_document.components.find((item: { id: string; props?: Record<string, unknown> }) => item.id === "speaker")?.props as Record<string, unknown>;
    return { audio_asset_id: props?.audio_asset_id, speech_source: props?.speech_source, recording: props?.recording };
  }, { timeout: 10_000 }).toMatchObject({ speech_source: "audio" });
  const draft = draftSnapshot!;
  const draftProps = draft.draft_document.components.find((item: { id: string; props?: Record<string, unknown> }) => item.id === "speaker")?.props as Record<string, unknown>;
  expect(draftProps.audio_asset_id).toBeTruthy();
  expect(draftProps.recording).toMatchObject({ asset_id: draftProps.audio_asset_id });
  expect(draftProps.recording).toHaveProperty("transcript", expect.stringMatching(/^本月销售额 \d+ 元。$/));
  const published = await apiPost<ScreenRecord>(page, `/api/admin/screens/${created.id}/publish`, { expected_revision: draft.draft_revision });
  expect(published.published_document?.components.find((item: { id: string; props?: Record<string, unknown> }) => item.id === "speaker")?.props).toMatchObject({
    audio_asset_id: draftProps.audio_asset_id, speech_source: "audio",
  });
  const key = await generateDisplayKey(page, created.id);
  await page.goto(`/play/${created.id}?key=${encodeURIComponent(key)}`);
  const speaker = page.locator('[data-component-id="speaker"] .digital-human');
  await expect(speaker).toBeVisible();
  await speaker.getByRole("button", { name: "启用声音", exact: true }).click();
  await expect(speaker).toHaveAttribute("data-status", "speaking", { timeout: 8_000 });
  await expect(speaker.locator(".digital-human__subtitle")).toContainText("本月销售额 1,234 元。");
  const apiKey = await rotateEmbedApiKey(page);
  const ticket = await issueEmbedTicket(page, { apiKey, screenId: created.id });
  await page.goto(`/e2e/embed-host.html?screen=${created.id}&ticket=${encodeURIComponent(ticket)}`);
  await expect(page.locator("#host-status")).toHaveText("ready");
  await expect(page.frameLocator("iframe").locator('[data-component-id="speaker"] .digital-human__subtitle')).toContainText("本月销售额 1,234 元。");
});

test("digital human embed commands report status and reject unknown components", async ({ page }) => {
  await authenticate(page);
  const screen = await createPublishedScreen(page, "数字人嵌入 " + Date.now(), broadcastDocument());
  const apiKey = await rotateEmbedApiKey(page);
  const ticket = await issueEmbedTicket(page, { apiKey, screenId: screen.id });
  await page.goto("/e2e/embed-host.html?screen=" + screen.id + "&ticket=" + encodeURIComponent(ticket));
  await expect(page.locator("#host-status")).toHaveText("ready");
  const speaker = page.frameLocator("iframe").locator('[data-component-id="speaker"]');
  await expect(speaker.locator(".digital-human__subtitle")).toHaveText("本月销售额 1,234 元。");
  const replies = await page.evaluate(async () => {
    const iframe = document.querySelector("iframe")!;
    const target = new URL(iframe.src).searchParams.get("instance_id");
    const send = (component_id: string) => new Promise<Record<string, unknown>>((resolve, reject) => {
      const request_id = crypto.randomUUID();
      const timer = setTimeout(() => { window.removeEventListener("message", receive); reject(new Error("No speech reply")); }, 5000);
      const receive = (event: MessageEvent) => {
        if (event.origin === location.origin && event.source === iframe.contentWindow && event.data.request_id === request_id) {
          clearTimeout(timer);
          window.removeEventListener("message", receive);
          resolve(event.data);
        }
      };
      window.addEventListener("message", receive);
      iframe.contentWindow!.postMessage({ type: "digitalHuman", instance_id: target, request_id, command: { component_id, action: "getStatus" } }, location.origin);
    });
    return [await send("speaker"), await send("outside-screen")];
  });
  expect(replies[0]!.type).toBe("digitalHumanStatus");
  expect(replies[0]!.state).toMatchObject({ component_id: "speaker", muted: true });
  expect(replies[1]!.code).toBe("DIGITAL_HUMAN_NOT_CONFIGURED");
  expect(await page.frameLocator("iframe").locator("body").evaluate(() => location.search)).toBe("");
  expect(appOrigin()).toContain("127.0.0.1");
});

test("cross-origin embed host loads the published digital human", async ({ page }) => {
  await authenticate(page);
  const screen = await createPublishedScreen(page, "数字人跨源嵌入 " + Date.now(), broadcastDocument());
  const apiKey = await rotateEmbedApiKey(page);
  const ticket = await issueEmbedTicket(page, {
    apiKey,
    screenId: screen.id,
    allowedOrigin: `http://localhost:${new URL(appOrigin()).port}`,
  });
  const hostOrigin = `http://localhost:${new URL(appOrigin()).port}`;
  await page.goto(
    `${hostOrigin}/e2e/embed-host.html?screen=${encodeURIComponent(screen.id)}&ticket=${encodeURIComponent(ticket)}&runtimeOrigin=${encodeURIComponent(appOrigin())}`,
  );
  expect(page.url()).toMatch(`${hostOrigin}/e2e/embed-host.html`);
  await expect(page.locator("#host-status")).toHaveText("ready");
  const frame = page.frameLocator("iframe");
  await expect(frame.locator('[data-component-id="speaker"] .digital-human__subtitle')).toHaveText("本月销售额 1,234 元。");
  expect(await frame.locator("body").evaluate(() => location.origin)).toBe(appOrigin());
  expect(await frame.locator("body").evaluate(() => location.search)).toBe("");
});

test("embed access revocation blocks and then restores an existing ticket", async ({ page }) => {
  await authenticate(page);
  const screen = await createPublishedScreen(page, "数字人访问撤销 " + Date.now(), broadcastDocument());
  const apiKey = await rotateEmbedApiKey(page);
  const ticket = await issueEmbedTicket(page, { apiKey, screenId: screen.id });
  await page.goto(`/e2e/embed-host.html?screen=${screen.id}&ticket=${encodeURIComponent(ticket)}`);
  await expect(page.locator("#host-status")).toHaveText("ready");
  const protectedEmbedUrl = await page.locator("iframe").getAttribute("src");
  expect(protectedEmbedUrl).toContain(`ticket=${encodeURIComponent(ticket)}`);
  const backendOrigin = `http://127.0.0.1:${loadRuntimeConfig().backendPort}`;
  const protectedDocumentUrl = `${backendOrigin}/api/embed/screens/${screen.id}`;

  await apiPatch(page, `/api/admin/screens/${screen.id}/access-policy`, {
    allowed_origins: ["https://other.example.com"],
  });
  const restricted = await apiGet<ScreenRecord>(page, `/api/admin/screens/${screen.id}`);
  expect(restricted.access_policy?.allowed_origins).toEqual(["https://other.example.com"]);
  const deniedFrame = page.frames().find((frame) => frame.url().includes(`/embed/${screen.id}`));
  expect(deniedFrame).toBeDefined();
  const deniedStatus = await deniedFrame!.evaluate(async ({ url, bearer }) => {
    const response = await fetch(url, {
      cache: "no-store",
      headers: { Authorization: `Bearer ${bearer}` },
    });
    return response.status;
  }, { url: protectedDocumentUrl, bearer: ticket });
  expect(deniedStatus).toBe(403);

  await apiPatch(page, `/api/admin/screens/${screen.id}/access-policy`, {
    allowed_origins: [appOrigin()],
  });
  const restoredFrame = page.frames().find((frame) => frame.url().includes(`/embed/${screen.id}`));
  expect(restoredFrame).toBeDefined();
  const restoredStatus = await restoredFrame!.evaluate(async ({ url, bearer }) => {
    const response = await fetch(url, {
      cache: "no-store",
      headers: { Authorization: `Bearer ${bearer}` },
    });
    return response.status;
  }, { url: protectedDocumentUrl, bearer: ticket });
  expect(restoredStatus).toBe(200);
  await expect(page.frameLocator("iframe").locator('[data-component-id="speaker"] .digital-human__subtitle')).toHaveText("本月销售额 1,234 元。");
});

function imageFixture(color: string): Buffer {
  return execFileSync("ffmpeg", ["-v", "error", "-f", "lavfi", "-i", `color=c=${color}:s=128x96`, "-frames:v", "1", "-f", "image2pipe", "-c:v", "png", "-"], { timeout: 20000 });
}

test("confirmed video broadcasts use real audio and subtitle clocks across pause and mute", async ({ page }, info) => {
  await authenticate(page);
  const videoPath = info.outputPath("recording.mp4");
  execFileSync("ffmpeg", [
    "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=15",
    "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100", "-t", "8",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", videoPath,
  ], { timeout: 20000 });
  const upload = async (name: string, mimeType: string, buffer: Buffer): Promise<ScreenAssetResponse> => {
    const response = await page.request.post(`${appOrigin()}/api/admin/assets`, {
      headers: await mutationHeaders(page), multipart: { file: { name, mimeType, buffer } },
    });
    expect(response.status()).toBe(201);
    return response.json() as Promise<ScreenAssetResponse>;
  };
  const media = await upload(`recording-${info.project.name}.mp4`, "video/mp4", readFileSync(videoPath));
  const subtitle = await upload("recording.vtt", "text/vtt", Buffer.from("WEBVTT\n\n00:00.000 --> 00:02.000\n测试第一句。\n\n00:02.000 --> 00:08.000\n测试第二句。\n"));
  const document = broadcastDocument();
  Object.assign(document.components[1]!.props, {
    speech_template: "测试第一句。测试第二句。", speaking_asset_id: media.id, speaking_kind: "video", speech_source: "video",
    auto_play: false, max_duration_seconds: 20,
    recording: { asset_id: media.id, sha256: media.sha256, duration_seconds: media.media!.duration_seconds,
      transcript: "测试第一句。测试第二句。", subtitle_asset_id: subtitle.id, subtitle_sha256: subtitle.sha256, cues: subtitle.media!.cues },
  });
  const screen = await createPublishedScreen(page, "真实视频播报 " + Date.now(), document);
  const key = await generateDisplayKey(page, screen.id);
  await page.goto(`/play/${screen.id}?key=${encodeURIComponent(key)}`);
  const speaker = page.locator(".digital-human");
  await expect(speaker).toBeVisible();
  await expect(speaker.getByRole("button", { name: "播放播报", exact: true })).toBeEnabled();
  await speaker.getByRole("button", { name: "启用声音", exact: true }).click();
  const video = speaker.locator(".digital-human__speech-video");
  await expect(speaker).toHaveAttribute("data-status", "speaking");
  await expect.poll(() => video.evaluate((node: HTMLVideoElement) => node.currentTime)).toBeGreaterThan(0.2);
  expect(await video.evaluate((node: HTMLVideoElement) => ({ muted: node.muted, loop: node.loop, width: node.videoWidth }))).toEqual({ muted: false, loop: false, width: 320 });
  const pixels = await video.evaluate((node: HTMLVideoElement) => {
    const canvas = window.document.createElement("canvas");
    canvas.width = 32; canvas.height = 24;
    const context = canvas.getContext("2d")!;
    context.drawImage(node, 0, 0, 32, 24);
    const data = context.getImageData(0, 0, 32, 24).data;
    return new Set(Array.from({ length: data.length / 4 }, (_, index) => `${data[index * 4]},${data[index * 4 + 1]},${data[index * 4 + 2]}`)).size;
  });
  expect(pixels).toBeGreaterThan(20);
  await speaker.getByRole("button", { name: "暂停播报", exact: true }).click();
  const frozenTime = await video.evaluate((node: HTMLVideoElement) => node.currentTime);
  await page.waitForTimeout(1200);
  expect(await video.evaluate((node: HTMLVideoElement) => node.currentTime)).toBeCloseTo(frozenTime, 1);
  await speaker.getByRole("button", { name: "静音", exact: true }).click();
  await expect(speaker).toHaveAttribute("data-status", "paused");
  await speaker.getByRole("button", { name: "播放播报", exact: true }).click();
  await expect.poll(() => video.evaluate((node: HTMLVideoElement) => node.currentTime)).toBeGreaterThan(frozenTime + 0.2);
  expect(await video.evaluate((node: HTMLVideoElement) => node.volume)).toBe(0);
  await speaker.getByRole("button", { name: "启用声音", exact: true }).click();
  expect(await video.evaluate((node: HTMLVideoElement) => node.volume)).toBe(1);
  await video.evaluate((node: HTMLVideoElement) => { node.currentTime = 3; });
  await expect(speaker.locator(".is-current")).toHaveText("测试第二句。");
  await speaker.getByRole("button", { name: "暂停播报", exact: true }).click();
  const progress = Number(await speaker.getByRole("progressbar").getAttribute("aria-valuenow"));
  expect(progress).toBeGreaterThanOrEqual(37);
  expect(progress).toBeLessThan(70);
  const desktop = info.outputPath("recording-player-desktop.png");
  await page.screenshot({ path: desktop });
  await info.attach("recording-player-desktop", { path: desktop, contentType: "image/png" });
  await page.setViewportSize({ width: 390, height: 844 });
  const mobile = info.outputPath("recording-player-mobile.png");
  await page.screenshot({ path: mobile });
  await info.attach("recording-player-mobile", { path: mobile, contentType: "image/png" });
  expect(await speaker.evaluate((node) => node.scrollWidth <= node.clientWidth)).toBe(true);
  await speaker.getByRole("button", { name: "停止播报", exact: true }).click();
  await expect(video).not.toHaveAttribute("src", /.+/);

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`/studio/screens/${screen.id}/edit`);
  await page.locator('[data-canvas-component="speaker"]').click({ position: { x: 20, y: 120 } });
  await page.locator(".speech-inspector summary").filter({ hasText: /^声音$/ }).click();
  const editor = page.locator(".recording-editor");
  await expect(editor).toBeVisible();
  await expect(editor.getByLabel("录制文案", { exact: true })).toHaveValue("测试第一句。测试第二句。");
  await editor.getByLabel("字幕 1 结束秒数", { exact: true }).fill("1.750");
  await expect(editor.getByRole("button", { name: "确认录制内容" })).toBeDisabled();
  await editor.getByLabel("已核对录音、文案与字幕").check();
  await editor.getByRole("button", { name: "确认录制内容" }).click();
  await expect(editor.locator("span[role='status']")).toHaveText("已确认版本");
  await expect.poll(async () => {
    const saved = await apiGet<{ draft_document: { components: { props: { recording?: { subtitle_asset_id: string; cues: { end: number }[] } } }[] } }>(page, `/api/admin/screens/${screen.id}`);
    return saved.draft_document.components[1]!.props.recording?.cues[0]!.end;
  }).toBe(1.75);
  const editorShot = info.outputPath("recording-editor.png");
  await page.screenshot({ path: editorShot });
  await info.attach("recording-editor", { path: editorShot, contentType: "image/png" });
});

test("asset library preserves published versions and previews real media", async ({ page }, info) => {
  await authenticate(page);
  const colors = { chromium: ["0x14847c", "0x327cd4"], firefox: ["0x34847c", "0x527cd4"], webkit: ["0x54847c", "0x727cd4"] }[info.project.name]!;
  const original = imageFixture(colors[0]!);
  const replacement = imageFixture(colors[1]!);
  const response = await page.request.post(`${appOrigin()}/api/admin/assets`, {
    headers: await mutationHeaders(page), multipart: { file: { name: "avatar-original.png", mimeType: "image/png", buffer: original } },
  });
  expect(response.status()).toBe(201);
  const asset = await response.json() as { id: string };
  const screenDocument = broadcastDocument();
  Object.assign(screenDocument.components[1]!.props, { avatar_asset_id: asset.id });
  const screen = await createPublishedScreen(page, "资源版本测试 " + Date.now(), screenDocument);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`/studio/screens/${screen.id}/edit`);
  await page.locator('[data-canvas-component="speaker"]').click({ position: { x: 20, y: 120 } });
  const open = page.getByRole("button", { name: "选择待机形象", exact: true });
  await open.click();
  const dialog = page.getByRole("dialog", { name: "媒体资源库" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("searchbox", { name: "搜索资源" })).toBeFocused();
  await expect(dialog.locator(".asset-library__references")).toContainText("已发布");
  await expect(dialog.getByRole("button", { name: "删除资源版本" })).toBeDisabled();
  await expect.poll(() => dialog.locator(".asset-library__preview img").evaluate((image: HTMLImageElement) => image.naturalWidth)).toBe(128);
  await dialog.getByLabel("资源名称", { exact: true }).fill("播报头像 " + info.project.name);
  await dialog.getByLabel("授权备注", { exact: true }).fill("测试自制素材");
  await dialog.getByRole("button", { name: "保存信息" }).click();
  await expect(dialog).toContainText("资源信息已保存");
  await dialog.getByLabel("替换资源文件", { exact: true }).setInputFiles({ name: "avatar-next.png", mimeType: "image/png", buffer: replacement });
  await expect(dialog).toContainText("已创建版本 v2");
  const nextId = await dialog.locator(".asset-library__preview img").getAttribute("src");
  expect(nextId).not.toContain(asset.id);
  await expect(dialog.getByRole("button", { name: "使用此版本" })).toBeEnabled();
  const desktop = info.outputPath("asset-library-desktop.png");
  await page.screenshot({ path: desktop });
  await info.attach("asset-library-desktop", { path: desktop, contentType: "image/png" });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await dialog.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
  const mobile = info.outputPath("asset-library-mobile.png");
  await page.screenshot({ path: mobile });
  await info.attach("asset-library-mobile", { path: mobile, contentType: "image/png" });
  await dialog.getByRole("button", { name: "使用此版本" }).click();
  await expect(dialog).not.toBeVisible();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await expect(open).toBeFocused();
  const updated = await apiGet<{ published_document: { components: { props: Record<string, unknown> }[] } }>(page, `/api/admin/screens/${screen.id}`);
  expect(updated.published_document.components[1]!.props.avatar_asset_id).toBe(asset.id);
  const oldBytes = await page.request.get(`${appOrigin()}/api/admin/assets/${asset.id}`);
  expect(await oldBytes.body()).toEqual(original);

  await page.getByRole("button", { name: "资源库", exact: true }).click();
  const audioPath = info.outputPath("preview.wav");
  execFileSync("ffmpeg", ["-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=16000", "-t", "3", "-c:a", "pcm_s16le", audioPath], { timeout: 20000 });
  const audio = readFileSync(audioPath);
  const audioName = `preview-${info.project.name}.wav`;
  await dialog.getByLabel("上传资源文件", { exact: true }).setInputFiles({ name: audioName, mimeType: "audio/wav", buffer: audio });
  await expect(dialog.locator("audio")).toBeVisible();
  await expect.poll(() => dialog.locator("audio").evaluate((element: HTMLAudioElement) => element.readyState)).toBeGreaterThanOrEqual(1);
  await dialog.locator("audio").evaluate(async (element: HTMLAudioElement) => { await element.play(); });
  await expect.poll(() => dialog.locator("audio").evaluate((element: HTMLAudioElement) => element.currentTime)).toBeGreaterThan(0);
  await dialog.getByRole("searchbox", { name: "搜索资源" }).fill("播报头像 " + info.project.name);
  await dialog.getByRole("button", { name: "刷新资源" }).click();
  await expect(dialog.locator(".asset-library__item")).not.toHaveCount(0);
  const mediaStopped = page.evaluate(() => {
    const media = document.querySelector("dialog audio")! as HTMLAudioElement;
    return new Promise<boolean>((resolve) => { media.addEventListener("emptied", () => resolve(media.paused && !media.hasAttribute("src")), { once: true }); });
  });
  await dialog.locator(".asset-library__item").first().click();
  expect(await mediaStopped).toBe(true);
  await dialog.getByRole("button", { name: "关闭资源库" }).click();
  await expect(dialog).not.toBeVisible();
});
