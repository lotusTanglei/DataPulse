import { expect, test, vi } from "vitest";

import { createDataRuntime } from "./dataRuntime";
import {
  createMockBinding,
  resolveLocalResult,
} from "./mockData";

test("mock results are deterministic for a seed and vary across seeds", () => {
  const first = resolveLocalResult(
    { id: "line-a", type: "builtin.line" },
    createMockBinding("builtin.line", 42),
  );
  const same = resolveLocalResult(
    { id: "line-a", type: "builtin.line" },
    createMockBinding("builtin.line", 42),
  );
  const different = resolveLocalResult(
    { id: "line-a", type: "builtin.line" },
    createMockBinding("builtin.line", 43),
  );

  expect(first).toEqual(same);
  expect(first).not.toEqual(different);
  expect(first?.columns.map((column) => column.name)).toEqual([
    "日期",
    "序列-01",
    "序列-02",
  ]);
});

test("specialized list demos use neutral component-specific columns", () => {
  const status = resolveLocalResult(
    { id: "status-a", type: "builtin.status_matrix" },
    createMockBinding("builtin.status_matrix", 42),
  );
  const timeline = resolveLocalResult(
    { id: "timeline-a", type: "builtin.timeline" },
    createMockBinding("builtin.timeline", 42),
  );

  expect(status?.columns.map((column) => column.name)).toEqual([
    "对象",
    "状态",
    "更新时间",
  ]);
  expect(timeline?.columns.map((column) => column.name)).toEqual([
    "时间",
    "事件",
    "详情",
  ]);
  expect(status?.rows[0]?.[0]).toMatch(/^对象-/);
  expect(timeline?.rows[0]?.[1]).toMatch(/状态更新|数据同步|规则触发|配置变更|任务完成/);
});

test("static bindings are validated and adapted to QueryResult", () => {
  const result = resolveLocalResult(
    { id: "table-a", type: "builtin.table" },
    {
      source: "static",
      static_data: {
        schema_version: 1,
        columns: [
          { name: "类别", data_type: "string" },
          { name: "数值", data_type: "number" },
        ],
        rows: [["A", 12], ["B", null]],
      },
    },
  );

  expect(result).toMatchObject({
    request_id: "mock:table-a",
    row_count: 2,
    columns: [
      { name: "类别", data_type: "string" },
      { name: "数值", data_type: "number" },
    ],
  });
  expect(result?.rows).toEqual([["A", 12], ["B", null]]);
});

test("static and mock bindings bypass the query component", async () => {
  const query = vi.fn();
  const runtime = createDataRuntime(query);

  await runtime.load(
    "kpi-a",
    { source: "mock", mock_data: { preset: "single", seed: 5 } },
    {},
    "builtin.kpi",
  );
  await runtime.load(
    "table-a",
    {
      source: "static",
      static_data: {
        columns: [{ name: "value", data_type: "number" }],
        rows: [[10]],
      },
    },
    {},
    "builtin.table",
  );

  expect(query).not.toHaveBeenCalled();
  expect(runtime.state("kpi-a").status).toBe("success");
  expect(runtime.state("table-a").status).toBe("success");
});

test("invalid static row shapes become component errors", async () => {
  const runtime = createDataRuntime(vi.fn());

  await expect(
    runtime.load(
      "broken-table",
      {
        source: "static",
        static_data: {
          columns: [{ name: "value", data_type: "number" }],
          rows: [[1, 2]],
        },
      },
      {},
      "builtin.table",
    ),
  ).rejects.toThrow("静态数据行与字段数量不一致");
  expect(runtime.state("broken-table").status).toBe("error");
});
