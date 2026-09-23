# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: identity.spec.ts >> two accounts share a draft, reject stale edits, and revoke access
- Location: e2e/identity.spec.ts:12:1

# Error details

```
Error: Channel closed
```

```
Error: locator.selectOption: Test ended.
Call log:
  - waiting for getByRole('form', { name: '创建用户' }).getByLabel('角色', { exact: true })

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - complementary [ref=e4]:
    - generic "工作区导航" [ref=e5]:
      - generic [ref=e6]: D
      - generic [ref=e7]: DataPulse
      - generic [ref=e8]: ⌄
    - navigation "主导航" [ref=e9]:
      - link "概览" [ref=e10] [cursor=pointer]:
        - /url: /studio/overview
      - link "数据源" [ref=e17] [cursor=pointer]:
        - /url: /studio/datasources
      - link "数据集" [ref=e23] [cursor=pointer]:
        - /url: /studio/datasets
      - link "大屏" [ref=e28] [cursor=pointer]:
        - /url: /studio/screens
    - link "资源共享" [ref=e33] [cursor=pointer]:
      - /url: /studio/sharing
    - link "模板与插件" [ref=e38] [cursor=pointer]:
      - /url: /studio/ecosystem
    - link "用户管理" [ref=e43] [cursor=pointer]:
      - /url: /studio/users
    - region "最近访问" [ref=e48]:
      - paragraph [ref=e49]: 最近访问
      - paragraph [ref=e50]: 暂无最近项目
    - link "系统设置" [ref=e52] [cursor=pointer]:
      - /url: /studio/settings
    - generic [ref=e57]:
      - generic [ref=e58]: A
      - generic [ref=e59]: admin
      - button "退出管理员账号" [ref=e60] [cursor=pointer]
  - main [ref=e64]:
    - generic [ref=e65]:
      - navigation "面包屑" [ref=e66]:
        - generic [ref=e67]: DataPulse
        - generic [ref=e68]: /
        - strong [ref=e69]: 用户管理
      - generic [ref=e70]: 本地工作区
    - generic [ref=e72]:
      - generic [ref=e74]:
        - paragraph [ref=e75]: 工作区管理
        - heading "用户管理" [level=1] [ref=e76]
        - paragraph [ref=e77]: 管理登录账号和角色。资源通过共享授权，观看者的嵌入权限由宿主系统管理。
      - form "创建用户" [ref=e78]:
        - heading "创建用户" [level=2] [ref=e79]
        - generic [ref=e80]:
          - text: 用户名
          - textbox "用户名" [ref=e81]: collaborator-chromium-1789960378843
        - generic [ref=e82]:
          - text: 初始密码
          - textbox "初始密码" [active] [ref=e83]: identity-e2e-fixture-password
        - generic [ref=e84]:
          - text: 角色
          - combobox "角色" [ref=e85]:
            - option "只读用户" [selected]
            - option "编辑者"
            - option "管理员"
        - button "创建用户" [ref=e86] [cursor=pointer]
      - region "用户列表" [ref=e87]:
        - generic [ref=e88]:
          - heading "工作区用户" [level=2] [ref=e89]
          - button "刷新" [ref=e90]
        - table [ref=e92]:
          - rowgroup [ref=e93]:
            - row [ref=e94]:
              - columnheader "用户名" [ref=e95]
              - columnheader "角色" [ref=e96]
              - columnheader "状态" [ref=e97]
              - columnheader "操作" [ref=e98]
          - rowgroup [ref=e99]:
            - row [ref=e100]:
              - cell "admin" [ref=e101]
              - cell "管理员" [ref=e102]
              - cell "启用" [ref=e103]
              - cell [ref=e104]:
                - button "编辑用户：admin" [ref=e105]: 角色与密码
                - button "停用用户：admin" [ref=e106]: 停用
      - generic [ref=e108]:
        - heading "权限审计" [level=2] [ref=e109]
        - button "查看最近记录" [ref=e110]
```

# Test source

```ts
  1  | import { expect, test } from "@playwright/test";
  2  | 
  3  | import {
  4  |   apiGet,
  5  |   apiPost,
  6  |   appOrigin,
  7  |   authenticate,
  8  |   mutationHeaders,
  9  |   type ScreenRecord,
  10 | } from "./helpers.js";
  11 | 
  12 | test("two accounts share a draft, reject stale edits, and revoke access", async ({ page, browser }, info) => {
  13 |   test.setTimeout(75_000);
  14 |   await authenticate(page);
  15 |   const suffix = `${info.project.name}-${Date.now()}`;
  16 |   const username = `collaborator-${suffix}`;
  17 |   const password = "identity-e2e-fixture-password";
  18 |   const screenName = `协作权限 ${suffix}`;
  19 | 
  20 |   await page.goto("/studio/users");
  21 |   const createForm = page.getByRole("form", { name: "创建用户" });
  22 |   await createForm.getByLabel("用户名", { exact: true }).fill(username);
  23 |   await createForm.getByLabel("初始密码", { exact: true }).fill(password);
> 24 |   await createForm.getByLabel("角色", { exact: true }).selectOption("editor");
     |                                                      ^ Error: locator.selectOption: Test ended.
  25 |   await createForm.getByRole("button", { name: "创建用户", exact: true }).click();
  26 |   await expect(page.getByRole("region", { name: "用户列表" }).getByText(username, { exact: true })).toBeVisible();
  27 |   await expect(createForm.getByLabel("初始密码", { exact: true })).toHaveValue("");
  28 |   const users = await apiGet<Array<{ id: string; username: string }>>(page, "/api/admin/users");
  29 |   const editorId = users.find((user) => user.username === username)!.id;
  30 |   const screen = await apiPost<ScreenRecord>(page, "/api/admin/screens", {
  31 |     name: screenName,
  32 |     draft_document: {
  33 |       schema_version: 1,
  34 |       canvas: { width: 960, height: 540 },
  35 |       components: [{
  36 |         id: "shared-title", type: "builtin.text",
  37 |         frame: { x: 40, y: 40, width: 600, height: 100 },
  38 |         props: { text: "初始共享标题", font_size: 30 },
  39 |       }],
  40 |     },
  41 |   });
  42 | 
  43 |   const editorContext = await browser.newContext({ baseURL: appOrigin() });
  44 |   const editor = await editorContext.newPage();
  45 |   try {
  46 |     await editor.goto("/studio/login");
  47 |     await editor.getByLabel("用户名", { exact: true }).fill(username);
  48 |     await editor.getByLabel("密码", { exact: true }).fill(password);
  49 |     await editor.getByRole("button", { name: "登录", exact: true }).click();
  50 |     await expect(editor).not.toHaveURL(/\/studio\/login$/);
  51 |     expect((await editor.request.get(`${appOrigin()}/api/admin/users`)).status()).toBe(403);
  52 |     await editor.goto("/studio/screens");
  53 |     await expect(editor.getByText(screenName, { exact: true })).toHaveCount(0);
  54 |     expect((await editor.request.get(`${appOrigin()}/api/admin/screens/${screen.id}`)).status()).toBe(404);
  55 | 
  56 |     await page.goto(`/studio/sharing?type=screen&id=${screen.id}`);
  57 |     await page.getByLabel("共享给", { exact: true }).selectOption(editorId);
  58 |     await page.getByLabel("权限", { exact: true }).selectOption("write");
  59 |     await page.getByRole("button", { name: "保存共享授权", exact: true }).click();
  60 |     await expect(page.getByText("共享授权已保存。数据集和媒体依赖需要分别授权。", { exact: true })).toBeVisible();
  61 | 
  62 |     await page.goto(`/studio/screens/${screen.id}/edit`);
  63 |     await editor.goto(`/studio/screens/${screen.id}/edit`);
  64 |     await expect(page.getByLabel("大屏编辑器")).toBeVisible();
  65 |     await expect(editor.getByLabel("大屏编辑器")).toBeVisible();
  66 |     await page.locator('[data-layer-id="shared-title"] span').first().click();
  67 |     await editor.locator('[data-layer-id="shared-title"] span').first().click();
  68 |     await editor.getByLabel("文本内容", { exact: true }).fill("编辑者保存的标题");
  69 |     await editor.getByLabel("文本内容", { exact: true }).blur();
  70 |     await expect.poll(async () => {
  71 |       const saved = await apiGet<ScreenRecord>(editor, `/api/admin/screens/${screen.id}`);
  72 |       return saved.draft_document.components[0].props.text;
  73 |     }).toBe("编辑者保存的标题");
  74 | 
  75 |     await page.getByLabel("文本内容", { exact: true }).fill("旧版本不能覆盖");
  76 |     await page.getByLabel("文本内容", { exact: true }).blur();
  77 |     await expect(page.getByText("草稿已在其他页面发生变化，请重新载入后继续编辑。", { exact: true })).toBeVisible();
  78 |     expect((await apiGet<ScreenRecord>(editor, `/api/admin/screens/${screen.id}`)).draft_document.components[0].props.text).toBe("编辑者保存的标题");
  79 |     const artifact = info.outputPath("identity-conflict.png");
  80 |     await page.screenshot({ path: artifact });
  81 |     await info.attach("identity-conflict", { path: artifact, contentType: "image/png" });
  82 | 
  83 |     await page.goto(`/studio/sharing?type=screen&id=${screen.id}`);
  84 |     page.once("dialog", (dialog) => dialog.accept());
  85 |     await page.getByRole("button", { name: `撤销授权：${username}`, exact: true }).click();
  86 |     await expect(page.getByText("共享授权已撤销。", { exact: true })).toBeVisible();
  87 |     expect((await editor.request.get(`${appOrigin()}/api/admin/screens/${screen.id}`)).status()).toBe(404);
  88 |     const deniedWrite = await editor.request.patch(`${appOrigin()}/api/admin/screens/${screen.id}`, {
  89 |       headers: await mutationHeaders(editor), data: { name: "撤销后不能修改" },
  90 |     });
  91 |     expect(deniedWrite.status()).toBe(404);
  92 |     await editor.goto("/studio/screens");
  93 |     await expect(editor.getByText(screenName, { exact: true })).toHaveCount(0);
  94 |   } finally {
  95 |     await editorContext.close();
  96 |   }
  97 | });
  98 | 
```