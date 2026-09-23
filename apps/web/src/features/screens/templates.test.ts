import { expect, test } from "vitest";

import type { Dataset } from "../datasets/types";
import {
  createTemplateDocument,
  createTemplatePlan,
  screenTemplates,
} from "./templates";

const dataset = {
  id: "sales",
  name: "销售数据",
  data_source_id: "warehouse",
  definition: {
    fields: [
      { name: "month", data_type: "date" },
      { name: "region", data_type: "string" },
      { name: "amount", data_type: "number" },
    ],
  },
} as Dataset;

test("provides five independent dashboard templates", () => {
  expect(screenTemplates).toHaveLength(5);
  expect(new Set(screenTemplates.map((template) => template.id)).size).toBe(5);

  for (const template of screenTemplates) {
    const document = createTemplateDocument(template.id);
    expect(document.canvas).toEqual({
      width: 1920,
      height: 1080,
      background: { color: "#08111f" },
    });
    const components = document.components ?? [];
    expect(components.length).toBeGreaterThanOrEqual(7);
    expect(new Set(components.map((component) => component.id)).size).toBe(
      components.length,
    );
    for (const component of components) {
      expect(component.frame.x).toBeGreaterThanOrEqual(0);
      expect(component.frame.y).toBeGreaterThanOrEqual(0);
      expect(component.frame.x + component.frame.width).toBeLessThanOrEqual(1920);
      expect(component.frame.y + component.frame.height).toBeLessThanOrEqual(1080);
    }
  }
});

test("returns a fresh document for each template creation", () => {
  const first = createTemplateDocument(screenTemplates[0].id);
  const second = createTemplateDocument(screenTemplates[0].id);
  const firstComponent = first.components?.[0];
  const secondComponent = second.components?.[0];
  if (!firstComponent || !secondComponent) {
    throw new Error("Template must contain components");
  }
  firstComponent.props = { ...(firstComponent.props ?? {}), text: "changed" };

  expect(secondComponent.props?.text).not.toBe("changed");
});

test("creates every manual template through a coordinate-free single-source plan", () => {
  for (const template of screenTemplates) {
    const plan = createTemplatePlan(template.id, dataset, "华东经营分析");
    expect(JSON.stringify(plan)).not.toContain('"frame"');
    expect(plan.layout?.template).toBe(template.planTemplate);
    expect(plan.dataset_ids).toEqual(["sales"]);
    expect(plan.widgets?.length).toBeGreaterThanOrEqual(2);
    expect(
      plan.widgets?.every((widget) => widget.dataset_id === "sales"),
    ).toBe(true);
  }
});

test("prefers business measures over numeric time and identifier fields", () => {
  const codedTimeDataset = {
    ...dataset,
    definition: {
      ...dataset.definition,
      fields: [
        { name: "month", data_type: "integer" },
        { name: "store_id", data_type: "integer" },
        { name: "amount", data_type: "number" },
      ],
    },
  } as Dataset;

  const plan = createTemplatePlan(
    "overview-grid",
    codedTimeDataset,
    "经营分析",
  );

  expect(
    plan.widgets?.flatMap((widget) => widget.measures ?? []).map((item) => item.field),
  ).toEqual(Array(8).fill("amount"));
  expect(plan.widgets?.map((widget) => widget.chart_type)).not.toContain(
    "heatmap",
  );
  expect(plan.widgets?.map((widget) => widget.chart_type)).not.toContain(
    "radar",
  );
});
