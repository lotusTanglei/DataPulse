import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";

import type { DashboardDocument } from "../../contracts";
import AiEditPanel from "./AiEditPanel.vue";

const document: DashboardDocument = {
  schema_version: 1,
  canvas: { width: 1920, height: 1080, background: {} },
  theme: { id: "datapulse-dark", tokens: {} },
  refresh: { mode: "disabled", interval_seconds: null },
  parameters: [],
  components: [
    {
      id: "title",
      type: "builtin.text",
      frame: { x: 40, y: 40, width: 600, height: 80, z_index: 0 },
      state: { locked: false, hidden: false },
      props: { text: "旧标题", font_size: 24 },
      style: {},
      data_binding: {},
      interactions: [],
    },
  ],
};

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

test("previews AI edit commands and applies only after confirmation", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve(
        jsonResponse({
          commands: [
            {
              type: "update_props",
              component_id: "title",
              patch: { text: "华东销售分析" },
            },
          ],
          explanation: "将标题改为华东销售分析。",
          warnings: [],
        }),
      ),
    ),
  );
  const wrapper = mount(AiEditPanel, {
    props: {
      document,
      selectedComponentIds: ["title"],
      datasetIds: [],
    },
  });

  await wrapper.get('textarea[name="aiEditQuestion"]').setValue("把标题改成华东销售分析");
  await wrapper.get("form").trigger("submit");
  await flushPromises();

  expect(wrapper.text()).toContain("将标题改为华东销售分析");
  expect(wrapper.emitted("apply")).toBeUndefined();

  await wrapper.get('[data-action="confirm-ai-edit"]').trigger("click");

  expect(wrapper.emitted("apply")?.[0]?.[0]).toEqual([
    {
      type: "update_props",
      component_id: "title",
      patch: { text: "华东销售分析" },
    },
  ]);
});
