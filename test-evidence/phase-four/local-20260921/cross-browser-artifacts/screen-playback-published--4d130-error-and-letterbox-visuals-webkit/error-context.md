# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: screen-playback.spec.ts >> published screens retain stable dark, light, isolated-error, and letterbox visuals
- Location: e2e/screen-playback.spec.ts:33:1

# Error details

```
Error: {"error":{"code":"SCREEN_NAME_CONFLICT","message":"A screen with this name already exists.","request_id":"e0104d1c-fa27-4666-91da-da9b81c525ac","field_errors":[]}}

expect(received).toBe(expected) // Object.is equality

Expected: true
Received: false
```

# Test source

```ts
  1   | import { expect, type Page } from "@playwright/test";
  2   | 
  3   | import { loadRuntimeConfig } from "./runtime-config.js";
  4   | 
  5   | export const adminPassword = "datapulse-e2e-password";
  6   | 
  7   | export function appOrigin(): string {
  8   |   return `http://127.0.0.1:${loadRuntimeConfig().frontendPort}`;
  9   | }
  10  | 
  11  | async function responseJson<T>(
  12  |   response: Awaited<ReturnType<Page["request"]["get"]>>,
  13  | ): Promise<T> {
> 14  |   expect(response.ok(), await response.text()).toBe(true);
      |                                                ^ Error: {"error":{"code":"SCREEN_NAME_CONFLICT","message":"A screen with this name already exists.","request_id":"e0104d1c-fa27-4666-91da-da9b81c525ac","field_errors":[]}}
  15  |   return response.json() as Promise<T>;
  16  | }
  17  | 
  18  | export async function authenticate(page: Page): Promise<void> {
  19  |   const origin = appOrigin();
  20  |   const status = await responseJson<{ initialized: boolean }>(
  21  |     await page.request.get(`${origin}/api/auth/status`),
  22  |   );
  23  |   if (!status.initialized) {
  24  |     const setup = await page.request.post(`${origin}/api/auth/setup`, {
  25  |       headers: { Origin: origin },
  26  |       data: {
  27  |         code: "e2e-setup-code",
  28  |         username: "admin",
  29  |         password: adminPassword,
  30  |       },
  31  |     });
  32  |     expect(setup.status(), await setup.text()).toBe(201);
  33  |     return;
  34  |   }
  35  |   const session = await page.request.get(`${origin}/api/auth/session`);
  36  |   if (session.ok()) {
  37  |     return;
  38  |   }
  39  |   const login = await page.request.post(`${origin}/api/auth/login`, {
  40  |     headers: { Origin: origin },
  41  |     data: { username: "admin", password: adminPassword },
  42  |   });
  43  |   expect(login.status(), await login.text()).toBe(204);
  44  | }
  45  | 
  46  | export async function mutationHeaders(
  47  |   page: Page,
  48  | ): Promise<Record<string, string>> {
  49  |   const origin = appOrigin();
  50  |   const cookies = await page.context().cookies(origin);
  51  |   const csrf = cookies.find((cookie) => cookie.name === "datapulse_csrf");
  52  |   expect(csrf).toBeDefined();
  53  |   return {
  54  |     Origin: origin,
  55  |     "X-CSRF-Token": csrf!.value,
  56  |   };
  57  | }
  58  | 
  59  | export async function apiGet<T>(page: Page, path: string): Promise<T> {
  60  |   return responseJson<T>(
  61  |     await page.request.get(`${appOrigin()}${path}`),
  62  |   );
  63  | }
  64  | 
  65  | export async function apiPost<T>(
  66  |   page: Page,
  67  |   path: string,
  68  |   data?: unknown,
  69  |   authorization?: string,
  70  | ): Promise<T> {
  71  |   const headers = authorization
  72  |     ? { Authorization: `Bearer ${authorization}` }
  73  |     : await mutationHeaders(page);
  74  |   return responseJson<T>(
  75  |     await page.request.post(`${appOrigin()}${path}`, {
  76  |       headers,
  77  |       ...(data === undefined ? {} : { data }),
  78  |     }),
  79  |   );
  80  | }
  81  | 
  82  | export async function apiPatch<T>(
  83  |   page: Page,
  84  |   path: string,
  85  |   data: unknown,
  86  | ): Promise<T> {
  87  |   return responseJson<T>(
  88  |     await page.request.patch(`${appOrigin()}${path}`, {
  89  |       headers: await mutationHeaders(page),
  90  |       data,
  91  |     }),
  92  |   );
  93  | }
  94  | 
  95  | export interface AnalyticsDataset {
  96  |   id: string;
  97  |   data_source_id: string;
  98  |   definition: { fields: { name: string; data_type: string }[] };
  99  | }
  100 | 
  101 | export async function ensureAnalyticsDataset(
  102 |   page: Page,
  103 | ): Promise<AnalyticsDataset> {
  104 |   const sources = await apiGet<Array<{ id: string; name: string }>>(
  105 |     page,
  106 |     "/api/admin/datasources",
  107 |   );
  108 |   let source = sources.find((item) => item.name === "E2E 大屏数据库");
  109 |   if (!source) {
  110 |     source = await apiPost<{ id: string; name: string }>(
  111 |       page,
  112 |       "/api/admin/datasources",
  113 |       {
  114 |         name: "E2E 大屏数据库",
```