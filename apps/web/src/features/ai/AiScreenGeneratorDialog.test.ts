import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";

import AiScreenGeneratorDialog from "./AiScreenGeneratorDialog.vue";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

test("shows actionable component and field details for screen generation errors", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/admin/datasets") {
        return Promise.resolve(jsonResponse([{ id: "sales", name: "销售数据集" }]));
      }
      if (url === "/api/admin/ai/status") {
        return Promise.resolve(jsonResponse({ status: "configured", model: "test" }));
      }
      if (url === "/api/admin/ai/screen" && init?.method === "POST") {
        return Promise.resolve(
          jsonResponse(
            {
              error: {
                code: "AI_FIELD_UNKNOWN",
                message: "AI 使用了未知字段，请检查组件和字段绑定。",
                request_id: "screen-error-1",
                field_errors: [
                  {
                    component_id: "sales-chart",
                    field: "data_binding.chart_spec.dimensions[0]",
                    reason: "字段不存在于数据集",
                    expected: "已声明的数据集字段",
                  },
                ],
              },
            },
            422,
          ),
        );
      }
      throw new Error(`Unexpected request: ${url}`);
    }),
  );

  const wrapper = mount(AiScreenGeneratorDialog, { props: { open: true } });
  await flushPromises();
  await wrapper.get('input[name="aiScreenName"]').setValue("销售大屏");
  await wrapper.get('textarea[name="aiScreenQuestion"]').setValue("生成销售分析");
  await wrapper.get('input[name="aiScreenDatasets"]').setValue(true);
  await wrapper.get("form").trigger("submit");
  await flushPromises();

  expect(wrapper.text()).toContain("sales-chart");
  expect(wrapper.text()).toContain("data_binding.chart_spec.dimensions[0]");
  expect(wrapper.text()).toContain("字段不存在于数据集");
  expect(wrapper.text()).toContain("已声明的数据集字段");
});
