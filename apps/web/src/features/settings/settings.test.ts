import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";

import DigitalHumanSettingsView from "./DigitalHumanSettingsView.vue";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const settings = {
  enabled: true,
  default_muted: false,
  default_subtitles: true,
  max_speech_seconds: 30,
  cooldown_seconds: 5,
  daily_task_limit: 1000,
  daily_audio_seconds_limit: 36000,
  ai_enabled: true,
  ai_model: "",
  ai_context_limit: 100,
  data_retention_days: 30,
  updated_at: "2026-09-09T00:00:00Z",
};

const provider = {
  id: "provider-1",
  name: "测试供应商",
  provider_type: "openai_compatible",
  base_url: "https://tts.example.com",
  default_voice: "alloy",
  language: "zh-CN",
  enabled: true,
  configured: true,
  cost_per_minute: 0,
  provider_version: "v1",
  health_status: "healthy",
  consecutive_failures: 0,
  circuit_open_until: null,
  last_checked_at: null,
  last_latency_ms: null,
  last_error_code: null,
};

const usage = {
  period_start: "2026-09-09T00:00:00Z",
  task_count: 4,
  succeeded_count: 3,
  failed_count: 1,
  generated_seconds: 12.4,
  cached_count: 2,
  estimated_cost: 1.24,
};

const metrics = {
  collected_at: "2026-09-09T00:00:00Z",
  tasks_queued: 4,
  tasks_succeeded: 3,
  tasks_failed: 1,
  tasks_cancelled: 0,
  cache_hits: 2,
  synthesis_attempts: 2,
  synthesis_failures: 1,
  synthesis_total_ms: 240,
  average_synthesis_ms: 120,
};

const costReport = {
  period_start: "2026-09-09T00:00:00Z",
  period_end: "2026-09-10T00:00:00Z",
  rows: [{ provider_id: "provider-1", provider_name: "测试供应商", task_count: 4, succeeded_count: 3, failed_count: 1, cached_count: 2, generated_seconds: 12.4, estimated_cost: 1.24 }],
  total_task_count: 4,
  total_generated_seconds: 12.4,
  total_estimated_cost: 1.24,
};

const tasks = [
  {
    id: "task-1",
    plan_id: "plan-1",
    status: "succeeded",
    provider_id: "provider-1",
    asset_id: "asset-1",
    error_code: null,
    created_at: "2026-09-09T00:00:00Z",
    started_at: "2026-09-09T00:00:01Z",
    finished_at: "2026-09-09T00:00:02Z",
  },
];

const audit = [{
  id: "audit-1",
  created_at: "2026-09-09T00:00:02Z",
  actor: "system",
  action: "speech.failed",
  resource_type: "task",
  resource_id: "task-1",
  request_id: null,
  details: { error_code: "SPEECH_TASK_FAILED" },
}];
const expiringAsset = {
  id: "avatar-1",
  name: "主播头像",
  original_name: "avatar.png",
  asset_type: "image",
  mime_type: "image/png",
  sha256: "a".repeat(64),
  size_bytes: 100,
  family_id: "avatar-1",
  version: 1,
  media: { validated: true },
  has_thumbnail: false,
  license_note: "授权到期提醒",
  license_expires_at: "2026-09-20T00:00:00Z",
  uploaded_by: "admin",
  created_at: "2026-01-01T00:00:00Z",
};

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("loads persisted runtime settings, providers, and usage", async () => {
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/settings")) return Promise.resolve(jsonResponse(settings));
    if (url.endsWith("/providers")) return Promise.resolve(jsonResponse([provider]));
    if (url.endsWith("/usage")) return Promise.resolve(jsonResponse(usage));
    if (url.endsWith("/metrics")) return Promise.resolve(jsonResponse(metrics));
    if (url.endsWith("/usage/cost")) return Promise.resolve(jsonResponse(costReport));
    if (url.includes("/providers/provider-1/health")) return Promise.resolve(jsonResponse([]));
    if (url.includes("/tasks")) return Promise.resolve(jsonResponse(tasks));
    if (url.includes("/audit")) return Promise.resolve(jsonResponse(audit));
    if (url.includes("/api/admin/assets/expiring")) return Promise.resolve(jsonResponse([expiringAsset]));
    return Promise.resolve(jsonResponse({ error: { code: "NOT_FOUND", message: "not found", request_id: "", field_errors: [] } }, 404));
  });
  vi.stubGlobal("fetch", fetchMock);

  const wrapper = mount(DigitalHumanSettingsView);
  await flushPromises();

  expect(wrapper.get("h1").text()).toBe("数字人设置");
  expect(wrapper.text()).toContain("测试供应商");
  expect(wrapper.text()).toContain("4");
  expect(wrapper.text()).toContain("运行指标");
  expect(wrapper.text()).toContain("资源授权即将到期");
  expect((wrapper.get('input[type="number"]').element as HTMLInputElement).value).toBe("30");
  expect(fetchMock).toHaveBeenCalledWith("/api/admin/digital-human/settings", expect.anything());
});

test("saves settings, tests a provider, and deletes it", async () => {
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/settings") && (!init?.method || init.method === "GET")) return Promise.resolve(jsonResponse(settings));
    if (url.endsWith("/providers") && (!init?.method || init.method === "GET")) return Promise.resolve(jsonResponse([provider]));
    if (url.endsWith("/usage")) return Promise.resolve(jsonResponse(usage));
    if (url.endsWith("/metrics")) return Promise.resolve(jsonResponse(metrics));
    if (url.endsWith("/usage/cost")) return Promise.resolve(jsonResponse(costReport));
    if (url.includes("/providers/provider-1/health")) return Promise.resolve(jsonResponse([]));
    if (url.includes("/tasks")) return Promise.resolve(jsonResponse(tasks));
    if (url.includes("/audit")) return Promise.resolve(jsonResponse(audit));
    if (url.endsWith("/settings") && init?.method === "PATCH") return Promise.resolve(jsonResponse({ ...settings, enabled: false }));
    if (url.endsWith("/providers/provider-1/test")) return Promise.resolve(jsonResponse({ ok: true, latency_ms: 18, error_code: null, voices: ["alloy"] }));
    if (url.endsWith("/providers/provider-1") && init?.method === "DELETE") return Promise.resolve(new Response(null, { status: 204 }));
    return Promise.resolve(jsonResponse({ error: { code: "NOT_FOUND", message: "not found", request_id: "", field_errors: [] } }, 404));
  });
  vi.stubGlobal("fetch", fetchMock);
  vi.stubGlobal("confirm", vi.fn(() => true));

  const wrapper = mount(DigitalHumanSettingsView);
  await flushPromises();
  await wrapper.get('input[type="checkbox"]').setValue(false);
  await wrapper.get("form").trigger("submit");
  await flushPromises();
  expect(
    fetchMock.mock.calls.some(
      ([url, init]) =>
        String(url).endsWith("/settings") && (init as RequestInit | undefined)?.method === "PATCH",
    ),
  ).toBe(true);

  await wrapper.get('button[aria-label="删除供应商：测试供应商"]').trigger("click");
  await flushPromises();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/admin/digital-human/providers/provider-1",
    expect.objectContaining({ method: "DELETE" }),
  );
});

test("submits each governance textarea line as a separate rule", async () => {
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/settings") && (!init?.method || init.method === "GET")) return Promise.resolve(jsonResponse(settings));
    if (url.endsWith("/providers")) return Promise.resolve(jsonResponse([]));
    if (url.endsWith("/usage")) return Promise.resolve(jsonResponse(usage));
    if (url.endsWith("/metrics")) return Promise.resolve(jsonResponse(metrics));
    if (url.endsWith("/usage/cost")) return Promise.resolve(jsonResponse(costReport));
    if (url.includes("/tasks")) return Promise.resolve(jsonResponse([]));
    if (url.includes("/audit")) return Promise.resolve(jsonResponse([]));
    if (url.endsWith("/api/admin/assets/expiring")) return Promise.resolve(jsonResponse([]));
    if (url.endsWith("/settings") && init?.method === "PATCH") return Promise.resolve(jsonResponse(settings));
    return Promise.resolve(jsonResponse({ error: { code: "NOT_FOUND", message: "not found", request_id: "", field_errors: [] } }, 404));
  });
  vi.stubGlobal("fetch", fetchMock);

  const wrapper = mount(DigitalHumanSettingsView);
  await flushPromises();
  const textareas = wrapper.findAll("textarea");
  await textareas[0]!.setValue("spam\n广告");
  await textareas[1]!.setValue("^secret$\n^token$");
  await wrapper.findAll("form")[1]!.trigger("submit");
  await flushPromises();

  const patchCall = fetchMock.mock.calls.find(([url, init]) =>
    String(url).endsWith("/settings") && (init as RequestInit | undefined)?.method === "PATCH",
  );
  expect(patchCall).toBeDefined();
  const body = JSON.parse(String((patchCall![1] as RequestInit).body));
  expect(body.forbidden_words).toEqual(["spam", "广告"]);
  expect(body.sensitive_patterns).toEqual(["^secret$", "^token$"]);
});

test("clears unreferenced speech cache after explicit confirmation", async () => {
  const failedTask = { ...tasks[0], status: "failed", error_code: "SPEECH_PROVIDER_UNAVAILABLE" };
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/settings")) return Promise.resolve(jsonResponse(settings));
    if (url.endsWith("/providers")) return Promise.resolve(jsonResponse([provider]));
    if (url.endsWith("/usage")) return Promise.resolve(jsonResponse(usage));
    if (url.endsWith("/metrics")) return Promise.resolve(jsonResponse(metrics));
    if (url.endsWith("/usage/cost")) return Promise.resolve(jsonResponse(costReport));
    if (url.includes("/providers/provider-1/health")) return Promise.resolve(jsonResponse([]));
    if (url.includes("/tasks") && init?.method === "POST") return Promise.resolve(jsonResponse({ ...failedTask, id: "task-2", status: "queued", error_code: null }));
    if (url.includes("/tasks")) return Promise.resolve(jsonResponse([failedTask]));
    if (url.includes("/audit")) return Promise.resolve(jsonResponse(audit));
    if (url.endsWith("/cache/clear") && init?.method === "POST") {
      return Promise.resolve(jsonResponse({ detached_task_count: 2, deleted_asset_count: 1 }));
    }
    return Promise.resolve(jsonResponse({ error: { code: "NOT_FOUND", message: "not found", request_id: "", field_errors: [] } }, 404));
  });
  vi.stubGlobal("fetch", fetchMock);
  vi.stubGlobal("confirm", vi.fn(() => true));

  const wrapper = mount(DigitalHumanSettingsView);
  await flushPromises();
  const clearButton = wrapper.findAll("button").find((button) => button.text().includes("清空未引用缓存"));
  expect(clearButton).toBeDefined();
  await clearButton!.trigger("click");
  await flushPromises();

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/admin/digital-human/cache/clear",
    expect.objectContaining({ method: "POST" }),
  );
  const retryButton = wrapper.findAll("button").find((button) => button.text().includes("重试"));
  expect(retryButton).toBeDefined();
  await retryButton!.trigger("click");
  await flushPromises();
  expect(fetchMock.mock.calls.some(([url, init]) => String(url).includes("/plans/plan-1/tasks") && (init as RequestInit | undefined)?.method === "POST")).toBe(true);
});
