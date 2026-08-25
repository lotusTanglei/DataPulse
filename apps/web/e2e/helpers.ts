import { expect, type Page } from "@playwright/test";

import { loadRuntimeConfig } from "./runtime-config.js";

export const adminPassword = "datapulse-e2e-password";

export function appOrigin(): string {
  return `http://127.0.0.1:${loadRuntimeConfig().frontendPort}`;
}

async function responseJson<T>(
  response: Awaited<ReturnType<Page["request"]["get"]>>,
): Promise<T> {
  expect(response.ok(), await response.text()).toBe(true);
  return response.json() as Promise<T>;
}

export async function authenticate(page: Page): Promise<void> {
  const origin = appOrigin();
  const status = await responseJson<{ initialized: boolean }>(
    await page.request.get(`${origin}/api/auth/status`),
  );
  if (!status.initialized) {
    const setup = await page.request.post(`${origin}/api/auth/setup`, {
      headers: { Origin: origin },
      data: {
        code: "e2e-setup-code",
        username: "admin",
        password: adminPassword,
      },
    });
    expect(setup.status(), await setup.text()).toBe(201);
    return;
  }
  const session = await page.request.get(`${origin}/api/auth/session`);
  if (session.ok()) {
    return;
  }
  const login = await page.request.post(`${origin}/api/auth/login`, {
    headers: { Origin: origin },
    data: { username: "admin", password: adminPassword },
  });
  expect(login.status(), await login.text()).toBe(204);
}

export async function mutationHeaders(
  page: Page,
): Promise<Record<string, string>> {
  const origin = appOrigin();
  const cookies = await page.context().cookies(origin);
  const csrf = cookies.find((cookie) => cookie.name === "datapulse_csrf");
  expect(csrf).toBeDefined();
  return {
    Origin: origin,
    "X-CSRF-Token": csrf!.value,
  };
}

export async function apiGet<T>(page: Page, path: string): Promise<T> {
  return responseJson<T>(
    await page.request.get(`${appOrigin()}${path}`),
  );
}

export async function apiPost<T>(
  page: Page,
  path: string,
  data?: unknown,
  authorization?: string,
): Promise<T> {
  const headers = authorization
    ? { Authorization: `Bearer ${authorization}` }
    : await mutationHeaders(page);
  return responseJson<T>(
    await page.request.post(`${appOrigin()}${path}`, {
      headers,
      ...(data === undefined ? {} : { data }),
    }),
  );
}

export async function apiPatch<T>(
  page: Page,
  path: string,
  data: unknown,
): Promise<T> {
  return responseJson<T>(
    await page.request.patch(`${appOrigin()}${path}`, {
      headers: await mutationHeaders(page),
      data,
    }),
  );
}

export interface AnalyticsDataset {
  id: string;
  data_source_id: string;
  definition: { fields: { name: string; data_type: string }[] };
}

export async function ensureAnalyticsDataset(
  page: Page,
): Promise<AnalyticsDataset> {
  const sources = await apiGet<Array<{ id: string; name: string }>>(
    page,
    "/api/admin/datasources",
  );
  let source = sources.find((item) => item.name === "E2E 大屏数据库");
  if (!source) {
    source = await apiPost<{ id: string; name: string }>(
      page,
      "/api/admin/datasources",
      {
        name: "E2E 大屏数据库",
        config: { type: "sqlite", path: "sales.db" },
      },
    );
  }
  const datasets = await apiGet<AnalyticsDataset[]>(
    page,
    "/api/admin/datasets",
  );
  const existing = datasets.find(
    (item) => item.data_source_id === source!.id &&
      item.definition.fields.some((field) => field.name === "area_code"),
  );
  if (existing) {
    return existing;
  }
  return apiPost<AnalyticsDataset>(page, "/api/admin/datasets", {
    name: "E2E 大屏销售数据",
    data_source_id: source.id,
    sql: "SELECT month, region, amount, target, area_code FROM sales",
    max_rows: 500,
    timeout_seconds: 10,
  });
}

export async function uploadVisualAssets(
  page: Page,
): Promise<{ imageId: string; mapId: string }> {
  const headers = await mutationHeaders(page);
  const image = await page.request.post(`${appOrigin()}/api/admin/assets`, {
    headers,
    multipart: {
      file: {
        name: "pixel.png",
        mimeType: "image/png",
        buffer: Buffer.from(
          "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
          "base64",
        ),
      },
    },
  });
  expect(image.status(), await image.text()).toBe(201);
  const map = await page.request.post(`${appOrigin()}/api/admin/assets`, {
    headers,
    multipart: {
      file: {
        name: "regions.geojson",
        mimeType: "application/geo+json",
        buffer: Buffer.from(
          JSON.stringify({
            type: "FeatureCollection",
            features: [
              {
                type: "Feature",
                properties: { code: "east", name: "华东" },
                geometry: {
                  type: "Polygon",
                  coordinates: [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]],
                },
              },
              {
                type: "Feature",
                properties: { code: "south", name: "华南" },
                geometry: {
                  type: "Polygon",
                  coordinates: [[[2, 0], [4, 0], [4, 2], [2, 2], [2, 0]]],
                },
              },
              {
                type: "Feature",
                properties: { code: "north", name: "华北" },
                geometry: {
                  type: "Polygon",
                  coordinates: [[[1, 2], [3, 2], [3, 4], [1, 4], [1, 2]]],
                },
              },
            ],
          }),
        ),
      },
    },
  });
  expect(map.status(), await map.text()).toBe(201);
  return {
    imageId: String((await image.json()).id),
    mapId: String((await map.json()).id),
  };
}

type DashboardDocument = Record<string, any>;

function chartSpec(
  datasetId: string,
  type: string,
  dimensions: string[],
  field: string,
  filters: unknown[] = [],
): Record<string, unknown> {
  return {
    schema_version: 1,
    dataset_id: datasetId,
    dimensions,
    measures: [{ field, aggregation: "sum" }],
    filters,
    sort: [],
    limit: 500,
    visual: { type, title: "" },
  };
}

export function configureNineComponentDocument(
  source: DashboardDocument,
  datasetId: string,
  assets: { imageId: string; mapId: string },
  theme: "dark" | "light" = "dark",
): DashboardDocument {
  const layouts: Record<string, [number, number, number, number]> = {
    "builtin.text": [40, 30, 1840, 80],
    "builtin.kpi": [40, 130, 300, 170],
    "builtin.progress": [360, 130, 430, 170],
    "builtin.image": [810, 130, 400, 170],
    "builtin.geo_map": [1230, 130, 650, 410],
    "builtin.line": [40, 320, 560, 350],
    "builtin.bar": [620, 320, 590, 350],
    "builtin.pie": [40, 690, 500, 350],
    "builtin.table": [560, 690, 1320, 350],
  };
  const bindings: Record<string, Record<string, unknown>> = {
    "builtin.kpi": chartSpec(datasetId, "kpi", [], "amount"),
    "builtin.progress": chartSpec(datasetId, "progress", [], "target"),
    "builtin.line": chartSpec(datasetId, "line", ["region"], "amount"),
    "builtin.bar": chartSpec(
      datasetId,
      "bar",
      ["month"],
      "amount",
      [
        {
          field: "region",
          operator: "equals",
          value: { kind: "parameter", name: "region" },
        },
      ],
    ),
    "builtin.pie": chartSpec(datasetId, "pie", ["region"], "amount"),
    "builtin.table": chartSpec(
      datasetId,
      "table",
      ["month", "region"],
      "amount",
    ),
    "builtin.geo_map": chartSpec(
      datasetId,
      "map",
      ["area_code"],
      "amount",
    ),
  };
  const components = source.components.map(
    (component: Record<string, any>, index: number) => {
      const layout = layouts[component.type] ?? [40, 40, 320, 180];
      const next: Record<string, any> = {
        ...component,
        frame: {
          x: layout[0],
          y: layout[1],
          width: layout[2],
          height: layout[3],
          z_index: index,
        },
        data_binding: bindings[component.type]
          ? { chart_spec: bindings[component.type] }
          : {},
      };
      if (component.type === "builtin.text") {
        next.props = {
          ...component.props,
          text: "DataPulse 运营态势总览",
          align: "center",
          font_size: 34,
        };
      } else if (component.type === "builtin.image") {
        next.props = {
          ...component.props,
          asset_id: assets.imageId,
          alt: "品牌图像",
          fit: "contain",
        };
      } else if (component.type === "builtin.geo_map") {
        next.props = { ...component.props, asset_id: assets.mapId };
      } else if (component.type === "builtin.kpi") {
        next.props = { ...component.props, label: "销售总额" };
      } else if (component.type === "builtin.progress") {
        next.props = { ...component.props, label: "目标值" };
      }
      if (component.type === "builtin.line") {
        next.interactions = [
          {
            event: "click",
            action: "set_parameter",
            parameter: "region",
            field: "region",
          },
        ];
      }
      return next;
    },
  );
  const light = theme === "light";
  return {
    ...source,
    canvas: {
      ...source.canvas,
      background: { color: light ? "#f8fafc" : "#0b1020" },
    },
    theme: {
      id: light ? "datapulse-light" : "datapulse-dark",
      tokens: light
        ? {
            text_primary: "#0f172a",
            text_secondary: "#475569",
            component_surface: "#ffffff",
            component_border: "#cbd5e1",
            chart_colors: ["#2563eb", "#16a34a", "#d97706"],
          }
        : {
            text_primary: "#f8fafc",
            text_secondary: "#94a3b8",
            component_surface: "#111827",
            component_border: "#334155",
            chart_colors: ["#60a5fa", "#34d399", "#fbbf24"],
          },
    },
    refresh: { mode: "interval", interval_seconds: 10 },
    parameters: [
      {
        id: "region",
        name: "region",
        data_type: "string",
        default: "华东",
        mutable: true,
        allowed_values: ["华东", "华南", "华北"],
      },
      {
        id: "year",
        name: "year",
        data_type: "integer",
        default: 2026,
        mutable: false,
        allowed_values: [],
      },
    ],
    components,
  };
}

export function nineComponentDocument(
  datasetId: string,
  assets: { imageId: string; mapId: string },
  theme: "dark" | "light" = "dark",
): DashboardDocument {
  const defaults: Record<string, Record<string, unknown>> = {
    "builtin.text": { text: "文本", align: "left", font_size: 24 },
    "builtin.image": { asset_id: "", alt: "", fit: "cover" },
    "builtin.kpi": { label: "指标", precision: 0, empty_text: "暂无数据" },
    "builtin.table": { max_rows: 100, empty_text: "暂无数据" },
    "builtin.progress": {
      label: "进度",
      precision: 0,
      empty_text: "暂无数据",
    },
    "builtin.line": { empty_text: "暂无数据" },
    "builtin.bar": {
      orientation: "vertical",
      empty_text: "暂无数据",
    },
    "builtin.pie": { variant: "pie", empty_text: "暂无数据" },
    "builtin.geo_map": {
      asset_id: "",
      region_code_property: "code",
      region_name_property: "name",
      empty_text: "暂无数据",
    },
  };
  const types = Object.keys(defaults);
  return configureNineComponentDocument(
    {
      schema_version: 1,
      canvas: { width: 1920, height: 1080, background: {} },
      theme: { id: "datapulse-dark", tokens: {} },
      refresh: { mode: "disabled", interval_seconds: null },
      parameters: [],
      components: types.map((type, index) => ({
        id: `component-${index + 1}`,
        type,
        frame: {
          x: 40,
          y: 40,
          width: 320,
          height: 180,
          z_index: index,
        },
        state: { locked: false, hidden: false },
        props: defaults[type],
        style: {},
        data_binding: {},
        interactions: [],
      })),
    },
    datasetId,
    assets,
    theme,
  );
}

export interface ScreenRecord {
  id: string;
  name: string;
  draft_revision: number;
  draft_document: DashboardDocument;
  published_document: DashboardDocument | null;
  access_policy?: { allowed_origins: string[]; allowed_ips: string[] };
}

export async function createPublishedScreen(
  page: Page,
  name: string,
  document: DashboardDocument,
): Promise<ScreenRecord> {
  const created = await apiPost<ScreenRecord>(
    page,
    "/api/admin/screens",
    { name },
  );
  const saved = await apiPatch<ScreenRecord>(
    page,
    `/api/admin/screens/${created.id}`,
    { draft_document: document, expected_revision: 0 },
  );
  return apiPost<ScreenRecord>(
    page,
    `/api/admin/screens/${created.id}/publish`,
    { expected_revision: saved.draft_revision },
  );
}

export async function generateDisplayKey(
  page: Page,
  screenId: string,
): Promise<string> {
  const generated = await apiPost<{ key: string }>(
    page,
    `/api/admin/screens/${screenId}/display-key`,
  );
  return generated.key;
}

export async function rotateEmbedApiKey(page: Page): Promise<string> {
  const generated = await apiPost<{ api_key: string }>(
    page,
    "/api/admin/embed/api-key",
  );
  return generated.api_key;
}

export async function issueEmbedTicket(
  page: Page,
  options: {
    apiKey: string;
    screenId: string;
    allowedOrigin?: string;
    lifetimeSeconds?: number;
  },
): Promise<string> {
  const ticket = await apiPost<{ ticket: string }>(
    page,
    "/api/embed/tickets",
    {
      screen_id: options.screenId,
      allowed_origin: options.allowedOrigin ?? appOrigin(),
      parameters: { region: "华东" },
      mutable_parameters: ["region"],
      lifetime_seconds: options.lifetimeSeconds ?? 3600,
    },
    options.apiKey,
  );
  return ticket.ticket;
}
