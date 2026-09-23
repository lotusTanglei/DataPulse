import { expect, it } from "vitest";
import metricPlugin from "../../../../../examples/metric-plugin/src/index";
import type { PluginContext } from "@datapulse/plugin-sdk";
it("example renders only controlled query results and cleans up", () => {
  const element = document.createElement("div");
  const controller = new AbortController();
  const context: PluginContext = {
    instanceId: "example",
    props: { label: "Total", precision: 1 },
    result: {
      columns: [{ name: "value", data_type: "number" }],
      rows: [[42.34]],
      row_count: 1,
      truncated: false,
      duration_ms: 1,
      request_id: "test",
    },
    loading: false,
    error: null,
    theme: {},
    signal: controller.signal,
  };
  const handle = metricPlugin.components["org.datapulse.example.metric"].mount(
    element,
    context,
  );
  expect(element.textContent).toContain("42.3");
  expect(element.textContent).toContain("Total");
  handle.update({ ...context, props: { label: "<img src=x>", precision: 0 } });
  expect(element.querySelector("img")).toBeNull();
  expect(element.textContent).toContain("<img src=x>");
  controller.abort();
  handle.destroy();
  expect(element.childElementCount).toBe(0);
});
it("example selects a numeric value when connector column types are unknown", () => {
  const element = document.createElement("div");
  metricPlugin.components["org.datapulse.example.metric"].mount(element, {
    instanceId: "example",
    props: {},
    result: {
      columns: [
        { name: "region", data_type: "unknown" },
        { name: "amount", data_type: "unknown" },
      ],
      rows: [["East", 320.5]],
      row_count: 1,
      truncated: false,
      duration_ms: 1,
      request_id: "test",
    },
    loading: false,
    error: null,
    theme: {},
    signal: new AbortController().signal,
  });
  expect(element.querySelector("strong")?.textContent).toBe("321");
});
