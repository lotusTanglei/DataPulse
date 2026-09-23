import { expect, test } from "@playwright/test";

import {
  apiGet,
  apiPost,
  appOrigin,
  authenticate,
  mutationHeaders,
  type ScreenRecord,
} from "./helpers.js";

test("two accounts share a draft, reject stale edits, and revoke access", async ({ page, browser }, info) => {
  test.setTimeout(75_000);
  await authenticate(page);
  const suffix = `${info.project.name}-${Date.now()}`;
  const username = `collaborator-${suffix}`;
  const password = "identity-e2e-fixture-password";
  const screenName = `协作权限 ${suffix}`;

  await page.goto("/studio/users");
  const createForm = page.getByRole("form", { name: "创建用户" });
  await createForm.getByLabel("用户名", { exact: true }).fill(username);
  await createForm.getByLabel("初始密码", { exact: true }).fill(password);
  await createForm.getByLabel("角色", { exact: true }).selectOption("editor");
  await createForm.getByRole("button", { name: "创建用户", exact: true }).click();
  await expect(page.getByRole("region", { name: "用户列表" }).getByText(username, { exact: true })).toBeVisible();
  await expect(createForm.getByLabel("初始密码", { exact: true })).toHaveValue("");
  const users = await apiGet<Array<{ id: string; username: string }>>(page, "/api/admin/users");
  const editorId = users.find((user) => user.username === username)!.id;
  const screen = await apiPost<ScreenRecord>(page, "/api/admin/screens", {
    name: screenName,
    draft_document: {
      schema_version: 1,
      canvas: { width: 960, height: 540 },
      components: [{
        id: "shared-title", type: "builtin.text",
        frame: { x: 40, y: 40, width: 600, height: 100 },
        props: { text: "初始共享标题", font_size: 30 },
      }],
    },
  });

  const editorContext = await browser.newContext({ baseURL: appOrigin() });
  const editor = await editorContext.newPage();
  try {
    await editor.goto("/studio/login");
    await editor.getByLabel("用户名", { exact: true }).fill(username);
    await editor.getByLabel("密码", { exact: true }).fill(password);
    await editor.getByRole("button", { name: "登录", exact: true }).click();
    await expect(editor).not.toHaveURL(/\/studio\/login$/);
    expect((await editor.request.get(`${appOrigin()}/api/admin/users`)).status()).toBe(403);
    await editor.goto("/studio/screens");
    await expect(editor.getByText(screenName, { exact: true })).toHaveCount(0);
    expect((await editor.request.get(`${appOrigin()}/api/admin/screens/${screen.id}`)).status()).toBe(404);

    await page.goto(`/studio/sharing?type=screen&id=${screen.id}`);
    await page.getByLabel("共享给", { exact: true }).selectOption(editorId);
    await page.getByLabel("权限", { exact: true }).selectOption("write");
    await page.getByRole("button", { name: "保存共享授权", exact: true }).click();
    await expect(page.getByText("共享授权已保存。数据集和媒体依赖需要分别授权。", { exact: true })).toBeVisible();

    await page.goto(`/studio/screens/${screen.id}/edit`);
    await editor.goto(`/studio/screens/${screen.id}/edit`);
    await expect(page.getByLabel("大屏编辑器")).toBeVisible();
    await expect(editor.getByLabel("大屏编辑器")).toBeVisible();
    await page.locator('[data-layer-id="shared-title"] span').first().click();
    await editor.locator('[data-layer-id="shared-title"] span').first().click();
    await editor.getByLabel("文本内容", { exact: true }).fill("编辑者保存的标题");
    await editor.getByLabel("文本内容", { exact: true }).blur();
    await expect.poll(async () => {
      const saved = await apiGet<ScreenRecord>(editor, `/api/admin/screens/${screen.id}`);
      return saved.draft_document.components[0].props.text;
    }).toBe("编辑者保存的标题");

    await page.getByLabel("文本内容", { exact: true }).fill("旧版本不能覆盖");
    await page.getByLabel("文本内容", { exact: true }).blur();
    await expect(page.getByText("草稿已在其他页面发生变化，请重新载入后继续编辑。", { exact: true })).toBeVisible();
    expect((await apiGet<ScreenRecord>(editor, `/api/admin/screens/${screen.id}`)).draft_document.components[0].props.text).toBe("编辑者保存的标题");
    const artifact = info.outputPath("identity-conflict.png");
    await page.screenshot({ path: artifact });
    await info.attach("identity-conflict", { path: artifact, contentType: "image/png" });

    await page.goto(`/studio/sharing?type=screen&id=${screen.id}`);
    page.once("dialog", (dialog) => dialog.accept());
    await page.getByRole("button", { name: `撤销授权：${username}`, exact: true }).click();
    await expect(page.getByText("共享授权已撤销。", { exact: true })).toBeVisible();
    expect((await editor.request.get(`${appOrigin()}/api/admin/screens/${screen.id}`)).status()).toBe(404);
    const deniedWrite = await editor.request.patch(`${appOrigin()}/api/admin/screens/${screen.id}`, {
      headers: await mutationHeaders(editor), data: { name: "撤销后不能修改" },
    });
    expect(deniedWrite.status()).toBe(404);
    await editor.goto("/studio/screens");
    await expect(editor.getByText(screenName, { exact: true })).toHaveCount(0);
  } finally {
    await editorContext.close();
  }
});
