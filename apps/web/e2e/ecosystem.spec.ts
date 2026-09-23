import { execFileSync } from "node:child_process";
import { cpSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";
import {
  apiGet,
  apiPatch,
  apiPost,
  appOrigin,
  authenticate,
  ensureAnalyticsDataset,
  generateDisplayKey,
  mutationHeaders,
  rotateEmbedApiKey,
} from "./helpers.js";
import { loadRuntimeConfig, repositoryRoot } from "./runtime-config.js";

const runtime = loadRuntimeConfig();
const backendOrigin = `http://127.0.0.1:${runtime.backendPort}`;

const packagePath = resolve(
  repositoryRoot,
  "examples/metric-plugin/dist/org.datapulse.example.metrics-1.0.0.zip",
);
test.beforeAll(() => {
  test.setTimeout(120_000);
  // The iframe must run the current production build through the actual /embed route.
  execFileSync("pnpm", ["build:web"], { cwd: repositoryRoot });
  cpSync(resolve(repositoryRoot, "apps/web/dist"), runtime.staticDir, { recursive: true });
  execFileSync(
    "pnpm",
    [
      "--filter",
      "@datapulse/web",
      "exec",
      "vite",
      "build",
      "--config",
      "../../examples/metric-plugin/vite.config.ts",
    ],
    { cwd: repositoryRoot },
  );
  execFileSync("python3", ["examples/metric-plugin/package.py"], {
    cwd: repositoryRoot,
  });
});

test("offline plugin installs, configures, queries and keeps its published version in player and Embed", async ({
  page,
}, info) => {
  test.setTimeout(90_000);
  await authenticate(page);
  const dataset = await ensureAnalyticsDataset(page);
  await page.goto("/studio/ecosystem");
  await page
    .getByLabel("离线安装包", { exact: false })
    .setInputFiles(packagePath);
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "导入安装包", exact: true }).click();
  await expect(
    page.locator('[data-package="org.datapulse.example.metrics@1.0.0"]'),
  ).toBeVisible();
  const screen = await apiPost<{ id: string }>(page, "/api/admin/screens", {
    name: `Plugin ${info.project.name} ${Date.now()}`,
  });
  await page.goto(`/studio/screens/${screen.id}/edit`);
  await page
    .getByRole("region", { name: "已安装插件" })
    .locator('[data-plugin-package="org.datapulse.example.metrics@1.0.0"]')
    .getByRole("button", { name: "示例指标", exact: true })
    .click();
  await page.locator('[data-inspector-tab="base"]').click();
  const label = page.locator('[data-property-name="label"] input');
  await expect(label).toBeVisible();
  await label.fill("Verified metric");
  await label.blur();
  await expect(page.locator(".plugin-renderer")).toContainText(
    "Verified metric",
  );
  await expect
    .poll(async () => {
      const current = await apiGet<any>(
        page,
        `/api/admin/screens/${screen.id}`,
      );
      return current.draft_document.components[0]?.props.label;
    })
    .toBe("Verified metric");
  const stored = await apiGet<any>(page, `/api/admin/screens/${screen.id}`);
  const component = stored.draft_document.components[0];
  component.data_binding = {
    chart_spec: {
      schema_version: 1,
      dataset_id: dataset.id,
      dimensions: ["region"],
      measures: [{ field: "amount", aggregation: "sum" }],
      filters: [],
      sort: [],
      limit: 20,
      visual: { type: "table", title: "" },
    },
  };
  const updated = await apiPatch<any>(page, `/api/admin/screens/${screen.id}`, {
    draft_document: stored.draft_document,
    expected_revision: stored.draft_revision,
  });
  const expected = await apiPost<any>(
    page,
    `/api/admin/screens/${screen.id}/query`,
    { component_id: component.id, parameters: {} },
  );
  const numericIndex = expected.rows[0].findIndex(
    (cell: unknown) => typeof cell === "number",
  );
  const number = Number(expected.rows[0][numericIndex]).toFixed(0);
  await apiPost(page, `/api/admin/screens/${screen.id}/publish`, {
    expected_revision: updated.draft_revision,
  });
  const key = await generateDisplayKey(page, screen.id);
  await page.goto(`/play/${screen.id}?key=${encodeURIComponent(key)}`);
  await expect(page.locator(".plugin-renderer strong")).toHaveText(number);
  await expect(page.locator(".plugin-renderer")).toContainText(
    "Verified metric",
  );
  const protectedRemoval = await page.request.delete(
    `${appOrigin()}/api/admin/ecosystem/packages/plugin/org.datapulse.example.metrics/1.0.0`,
    { headers: await mutationHeaders(page) },
  );
  expect(protectedRemoval.status()).toBe(409);
  const manifest = JSON.parse(
    readFileSync(
      resolve(repositoryRoot, "examples/metric-plugin/manifest.json"),
      "utf8",
    ),
  );
  manifest.version = "2.0.0";
  const module =
    "export default {apiVersion:1,components:{'org.datapulse.example.metric':{migrate(props){return {...props,label:props.label+' v2'};},mount(el){el.textContent='UPGRADED';return {update(){},destroy(){el.replaceChildren();}};}}}};";
  const upgraded = execFileSync("python3", [
    "-c",
    "import io,json,sys,zipfile; b=io.BytesIO(); z=zipfile.ZipFile(b,'w'); z.writestr(zipfile.ZipInfo('manifest.json'),sys.argv[1]); z.writestr(zipfile.ZipInfo('index.mjs'),sys.argv[2]); z.close(); sys.stdout.buffer.write(b.getvalue())",
    JSON.stringify(manifest),
    module,
  ]);
  const install = await page.request.post(
    `${appOrigin()}/api/admin/ecosystem/packages`,
    {
      headers: await mutationHeaders(page),
      multipart: {
        file: {
          name: "upgrade.zip",
          mimeType: "application/zip",
          buffer: upgraded,
        },
      },
    },
  );
  expect(install.status(), await install.text()).toBe(201);
  await page.reload();
  await expect(page.locator(".plugin-renderer strong")).toHaveText(number);
  await page.goto(`/studio/screens/${screen.id}/edit`);
  await page.locator('[data-plugin-package="org.datapulse.example.metrics@2.0.0"] [data-action="migrate-plugin"]').click();
  await expect(page.getByRole("status").filter({ hasText: "草稿已切换至 2.0.0" })).toBeVisible();
  await expect.poll(async () => {
    const current = await apiGet<any>(page, `/api/admin/screens/${screen.id}`);
    return {
      draftVersion: current.draft_document.plugin_dependencies[0].version,
      draftLabel: current.draft_document.components[0].props.label,
      publishedVersion: current.published_document.plugin_dependencies[0].version,
      publishedLabel: current.published_document.components[0].props.label,
    };
  }).toEqual({ draftVersion: "2.0.0", draftLabel: "Verified metric v2", publishedVersion: "1.0.0", publishedLabel: "Verified metric" });
  await page.goto(`/play/${screen.id}?key=${encodeURIComponent(key)}`);
  await expect(page.locator(".plugin-renderer strong")).toHaveText(number);
  const apiKey = await rotateEmbedApiKey(page);
  const { ticket } = await apiPost<{ ticket: string }>(page, "/api/embed/tickets", {screen_id: screen.id, allowed_origin: appOrigin(), lifetime_seconds:3600}, apiKey);
  const modules: Array<{
    authorization: string | undefined;
    cookie: string | undefined;
    url: string;
  }> = [];
  page.on("request", (request) => {
    if (
      request.url().includes("/api/embed/") &&
      request.url().includes("/files/index.mjs")
    )
      modules.push({
        authorization: request.headers().authorization,
        cookie: request.headers().cookie,
        url: request.url(),
      });
  });
  await page.addInitScript(() => {
    (window as any).__scriptViolations = [];
    document.addEventListener("securitypolicyviolation", (event) => {
      if (event.effectiveDirective.startsWith("script-src")) {
        (window as any).__scriptViolations.push(event.blockedURI);
      }
    });
  });
  const embedResponse = page.waitForResponse((response) => response.url().startsWith(`${backendOrigin}/embed/${screen.id}?`));
  await page.goto(`/e2e/embed-host.html?screen=${screen.id}&ticket=${encodeURIComponent(ticket)}&runtimeOrigin=${encodeURIComponent(backendOrigin)}`);
  const served = await embedResponse;
  expect(served.status()).toBe(200);
  expect(served.headers()["content-security-policy"]).toContain("script-src 'self' blob:");
  expect(served.headers()["content-security-policy"]).not.toContain("'unsafe-eval'");
  await expect(page.getByLabel("嵌入状态")).toHaveText("ready");
  await expect(
    page.frameLocator("iframe").locator(".plugin-renderer strong"),
  ).toHaveText(number);
  expect(await page.frameLocator("iframe").locator("body").evaluate(() => (window as any).__scriptViolations)).toEqual([]);
  expect(modules.length).toBeGreaterThan(0);
  expect(modules[0]?.authorization).toBe(`Bearer ${ticket}`);
  expect(modules[0]?.cookie).toBeUndefined();
  expect(modules[0]?.url).not.toContain(ticket);
});
