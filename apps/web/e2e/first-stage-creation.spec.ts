import { expect, test } from "@playwright/test";

import {
  apiGet,
  apiPatch,
  apiPost,
  appOrigin,
  authenticate,
  generateDisplayKey,
  type ScreenRecord,
} from "./helpers.js";
import { loadRuntimeConfig } from "./runtime-config.js";

test("template creation enters the shared screen editor", async ({ page }) => {
  await authenticate(page);
  await page.goto("/studio/screens");
  await page.getByRole("button", { name: "从模板创建" }).first().click();

  const dialog = page.getByRole("dialog", { name: "从模板创建" });
  await expect(dialog.getByLabel("大屏模板").getByRole("button")).toHaveCount(5);
  await dialog.getByLabel("大屏名称").fill("E2E 第一阶段模板入口");
  await dialog.getByRole("button", { name: "使用此模板" }).click();

  await expect(page.getByLabel("大屏编辑器")).toBeVisible();
  await expect(page.getByLabel("图层").locator("[data-layer-id]")).toHaveCount(9);
  await expect(page.getByText("经营分析总览")).toBeVisible();
});

test("blank creation supports hand editing, AI preview, confirmation, undo, redo, and playback", async ({
  page,
}) => {
  test.setTimeout(75_000);
  await authenticate(page);
  const publishRequests: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().includes("/publish")) {
      publishRequests.push(request.url());
    }
  });

  await page.goto("/studio/screens");
  await page.getByRole("button", { name: /新建大屏/ }).first().click();
  await page.getByLabel("大屏名称").fill("E2E 第一阶段交替创作");
  await page.getByRole("button", { name: "创建并编辑" }).click();
  await expect(page.getByLabel("大屏编辑器")).toBeVisible();

  await page.getByLabel("组件库").getByRole("button", { name: "＋ 文本" }).click();
  await page.getByLabel("图层").getByText("文本", { exact: true }).click();
  const textInput = page.getByLabel("文本内容");
  await textInput.fill("手工修改后的标题");
  await textInput.blur();
  await expect(textInput).toHaveValue("手工修改后的标题");

  const aiPanel = page.getByLabel("AI 修改");
  await aiPanel
    .getByLabel("修改要求")
    .fill("E2E_MODE:edit-title 把选中的标题改成 AI 版本");
  await aiPanel.getByRole("button", { name: "生成修改预览" }).click();
  await expect(page.getByLabel("AI 修改预览")).toBeVisible();
  await expect(page.getByText("E2E AI 已修改选中标题。", { exact: true })).toBeVisible();
  expect(publishRequests).toHaveLength(0);
  await expect(textInput).toHaveValue("手工修改后的标题");

  await page.getByRole("button", { name: "应用修改" }).click();
  await expect(textInput).toHaveValue("E2E AI 局部修改标题");

  await page.getByRole("button", { name: "撤销" }).click();
  await expect(textInput).toHaveValue("手工修改后的标题");
  await page.getByRole("button", { name: "重做" }).click();
  await expect(textInput).toHaveValue("E2E AI 局部修改标题");

  await textInput.fill("第二次手工修改标题");
  await textInput.blur();
  await aiPanel
    .getByLabel("修改要求")
    .fill("E2E_MODE:edit-title 再次基于最新画布调整标题");
  await aiPanel.getByRole("button", { name: "生成修改预览" }).click();
  await expect(page.getByLabel("AI 修改预览")).toBeVisible();
  await expect(textInput).toHaveValue("第二次手工修改标题");
  await page.getByRole("button", { name: "应用修改" }).click();
  await expect(textInput).toHaveValue("E2E AI 局部修改标题");

  await expect(page.getByLabel("编辑器工具栏").getByText("已保存")).toBeVisible({
    timeout: 12_000,
  });
  expect(publishRequests).toHaveLength(0);

  await page.getByRole("button", { name: "发布", exact: true }).click();
  await expect(page.getByRole("heading", { name: "确认发布大屏" })).toBeVisible();
  await page.getByRole("button", { name: "确认发布" }).click();
  await expect(page.getByText("发布完成")).toBeVisible();
  expect(publishRequests).toHaveLength(1);

  const screenId = page.url().match(/\/screens\/([^/]+)\/edit/)?.[1];
  expect(screenId).toBeTruthy();
  const stored = await apiGet<ScreenRecord>(
    page,
    `/api/admin/screens/${screenId}`,
  );
  expect(stored.draft_document.components?.[0]?.props?.text).toBe(
    "E2E AI 局部修改标题",
  );
  expect(stored.published_document?.components?.[0]?.props?.text).toBe(
    "E2E AI 局部修改标题",
  );

  const displayKey = await generateDisplayKey(page, screenId!);
  await page.goto(`/play/${screenId}?key=${encodeURIComponent(displayKey)}`);
  await expect(page).toHaveURL(new RegExp(`/play/${screenId}$`));
  await expect(page.getByText("E2E AI 局部修改标题")).toBeVisible();
});

test("screen access policy controls direct and embed authorization", async ({
  page,
}) => {
  await authenticate(page);
  await page.goto("/studio/screens");
  await page.getByRole("button", { name: /新建大屏/ }).first().click();
  await page.getByLabel("大屏名称").fill("E2E 第一阶段访问限制");
  await page.getByRole("button", { name: "创建并编辑" }).click();
  await expect(page.getByLabel("大屏编辑器")).toBeVisible();

  const screenId = page.url().match(/\/screens\/([^/]+)\/edit/)?.[1];
  expect(screenId).toBeTruthy();
  await page.getByRole("button", { name: "发布", exact: true }).click();
  await expect(page.getByRole("heading", { name: "确认发布大屏" })).toBeVisible();
  await page.getByRole("button", { name: "确认发布" }).click();
  await expect(page.getByText("发布完成")).toBeVisible();

  const accessPanel = page.getByLabel("访问限制");
  await accessPanel
    .getByLabel("允许的域名 / Origin")
    .fill("https://safe.example.com");
  await accessPanel.getByRole("button", { name: "保存访问限制" }).click();
  await expect(accessPanel.getByRole("button", { name: "保存访问限制" })).toBeEnabled();
  const policy = await apiGet<ScreenRecord>(
    page,
    `/api/admin/screens/${screenId}`,
  );
  expect(policy.access_policy).toEqual({
    allowed_origins: ["https://safe.example.com"],
    allowed_ips: [],
  });

  await page.reload();
  await expect(page.getByLabel("访问限制")).toBeVisible();

  const saved = await apiPatch<ScreenRecord>(
    page,
    `/api/admin/screens/${screenId}`,
    {
      draft_document: policy.draft_document,
      expected_revision: policy.draft_revision,
    },
  );
  const published = await apiPost<ScreenRecord>(
    page,
    `/api/admin/screens/${screenId}/publish`,
    { expected_revision: saved.draft_revision },
  );
  const displayKey = await generateDisplayKey(page, published.id);
  const denied = await page.request.post(
    `${appOrigin()}/api/player/screens/${published.id}/session`,
    {
      headers: { Origin: "https://evil.example.com" },
      data: { key: displayKey },
    },
  );
  expect(denied.status()).toBe(403);
  const allowed = await page.request.post(
    `${appOrigin()}/api/player/screens/${published.id}/session`,
    {
      headers: { Origin: "https://safe.example.com" },
      data: { key: displayKey },
    },
  );
  expect(allowed.status()).toBe(204);

  const ipPolicy = await apiPatch<ScreenRecord>(
    page,
    `/api/admin/screens/${screenId}/access-policy`,
    {
      allowed_origins: ["https://safe.example.com", appOrigin()],
      allowed_ips: ["127.0.0.1/32"],
    },
  );
  expect(ipPolicy.access_policy?.allowed_ips).toEqual(["127.0.0.1/32"]);
  const ipAllowed = await page.request.post(
    `${appOrigin()}/api/player/screens/${published.id}/session`,
    {
      headers: { Origin: "https://evil.example.com" },
      data: { key: displayKey },
    },
  );
  expect(ipAllowed.status()).toBe(204);

  const embedKey = await apiPost<{ api_key: string }>(page, "/api/admin/embed/api-key");
  const ticket = await apiPost<{ ticket: string }>(
    page,
    "/api/embed/tickets",
    {
      screen_id: published.id,
      allowed_origin: "https://safe.example.com",
      lifetime_seconds: 3600,
    },
    embedKey.api_key,
  );
  const backendOrigin = `http://127.0.0.1:${loadRuntimeConfig().backendPort}`;

  const iframeTicket = await apiPost<{ ticket: string }>(
    page,
    "/api/embed/tickets",
    {
      screen_id: published.id,
      allowed_origin: appOrigin(),
      lifetime_seconds: 3600,
    },
    embedKey.api_key,
  );
  await page.goto(
    `/e2e/embed-host.html?screen=${encodeURIComponent(published.id)}&ticket=${encodeURIComponent(iframeTicket.ticket)}`,
  );
  await expect(page.getByLabel("嵌入状态")).toHaveText("ready", {
    timeout: 12_000,
  });

  const wrongEmbedPage = await page.request.get(
    `${backendOrigin}/embed/${published.id}`,
    {
      params: { ticket: ticket.ticket },
      headers: { Origin: "https://evil.example.com" },
    },
  );
  expect(wrongEmbedPage.status()).toBe(403);
});
