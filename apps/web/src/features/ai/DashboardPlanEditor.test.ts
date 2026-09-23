import { mount } from "@vue/test-utils";
import { expect, test } from "vitest";

import type { DashboardPlan } from "../../contracts";
import DashboardPlanEditor from "./DashboardPlanEditor.vue";

function plan(): DashboardPlan {
  return {
    schema_version: 1,
    title: "销售总览",
    audience: "销售负责人",
    narrative: "先看指标，再看趋势。",
    dataset_ids: ["sales"],
    layout: {
      template: "executive-overview",
      grid_columns: 24,
      density: "comfortable",
      theme: "dark",
    },
    regions: [
      { id: "summary", kind: "summary", title: "核心指标", order: 0 },
      { id: "main", kind: "main", title: "趋势", order: 1 },
    ],
    widgets: [
      {
        id: "trend",
        title: "销售趋势",
        intent: "展示月度销售额趋势",
        region_id: "main",
        dataset_id: "sales",
        chart_type: "line",
        dimensions: ["month"],
        measures: [{ field: "amount", aggregation: "sum" }],
        filters: [],
        sort: [],
        limit: 1000,
      },
    ],
    parameters: [],
  };
}

test("edits measures, chart type, and region on the dashboard plan", async () => {
  const wrapper = mount(DashboardPlanEditor, { props: { modelValue: plan() } });

  await wrapper.get('[aria-label="删除指标 amount"]').trigger("click");
  let updates = wrapper.emitted<DashboardPlan[]>("update:modelValue") ?? [];
  expect(updates.at(-1)?.[0].widgets[0].measures).toEqual([]);

  await wrapper.setProps({ modelValue: updates.at(-1)?.[0] });
  await wrapper.get('[aria-label="新增指标"]').trigger("click");
  updates = wrapper.emitted<DashboardPlan[]>("update:modelValue") ?? [];
  expect(updates.at(-1)?.[0].widgets[0].measures).toEqual([
    { field: "", aggregation: "sum" },
  ]);

  await wrapper.setProps({ modelValue: updates.at(-1)?.[0] });
  await wrapper.get('[data-field="measure-field-0"]').setValue("orders");
  await wrapper.get('[data-field="chart-type"]').setValue("bar");
  await wrapper.get('[data-field="region"]').setValue("summary");

  updates = wrapper.emitted<DashboardPlan[]>("update:modelValue") ?? [];
  const edited = updates.at(-1)?.[0];
  expect(edited?.widgets[0]?.measures?.[0]?.field).toBe("orders");
  expect(edited?.widgets[0]?.chart_type).toBe("bar");
  expect(edited?.widgets[0]?.region_id).toBe("summary");
  expect(plan().widgets[0]?.chart_type).toBe("line");
});
