import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";

import AiAnalysisPanel from "./AiAnalysisPanel.vue";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("generates AI analysis and emits the selected chart suggestion", async () => {
  const chartSpec = {
    schema_version: 1,
    dataset_id: "sales",
    dimensions: ["region"],
    measures: [{ field: "amount", aggregation: "sum" }],
    filters: [],
    sort: [],
    limit: 1000,
    visual: { type: "table", title: "区域销售额" },
  };
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/admin/ai/analyze" && init?.method === "POST") {
      return Promise.resolve(
        jsonResponse({
          plan: {
            schema_version: 1,
            question: "按区域分析销售额",
            dataset_ids: ["sales"],
            dimensions: ["region"],
            measures: [{ field: "amount", aggregation: "sum" }],
            filters: [],
            sort: [],
            recommended_chart: "table",
            assumptions: [],
            requires_confirmation: true,
          },
          narrative: "建议先按区域汇总销售额，再观察差异。",
          chart_spec: chartSpec,
          warnings: ["结果基于当前数据样本。"],
        }),
      );
    }
    if (url === "/api/admin/ai/chart" && init?.method === "POST") {
      return Promise.resolve(
        jsonResponse({
          chart_spec: chartSpec,
          explanation: "表格更适合先核对区域汇总结果。",
          preview: {
            request_id: "ai-preview-1",
            columns: [
              { name: "region", data_type: "string" },
              { name: "amount", data_type: "number" },
            ],
            rows: [
              ["east", 120],
              ["west", 98],
            ],
            row_count: 2,
            truncated: false,
            duration_ms: 42,
          },
          warnings: [],
        }),
      );
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  const wrapper = mount(AiAnalysisPanel, {
    props: {
      fixedDatasetId: "sales",
      canApply: true,
    },
  });

  await wrapper.get('textarea[name="aiQuestion"]').setValue("按区域分析销售额");
  await wrapper.get("form").trigger("submit");
  await flushPromises();

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/admin/ai/analyze",
    expect.objectContaining({ method: "POST" }),
  );
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/admin/ai/chart",
    expect.objectContaining({ method: "POST" }),
  );
  expect(wrapper.text()).toContain("建议先按区域汇总销售额");
  expect(wrapper.text()).toContain("表格更适合先核对区域汇总结果");

  await wrapper.get("article button").trigger("click");

  expect(wrapper.emitted("apply-chart")?.[0]?.[0]).toMatchObject({
    dataset_id: "sales",
    visual: { type: "table", title: "区域销售额" },
  });
});
