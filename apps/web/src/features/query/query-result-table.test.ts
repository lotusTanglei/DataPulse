import { mount } from "@vue/test-utils";
import { expect, test } from "vitest";

import QueryResultTable from "./QueryResultTable.vue";
import type { QueryResult } from "./types";

function largeResult(): QueryResult {
  return {
    request_id: "query-5000",
    columns: [
      { name: "value", data_type: "text" },
      { name: "value", data_type: "numeric" },
      { name: "nullable", data_type: "text" },
      { name: "created_at", data_type: "datetime" },
      { name: "binary", data_type: "binary" },
    ],
    rows: Array.from({ length: 5000 }, (_, index) => [
      `row-${index}`,
      "9007199254740992",
      null,
      "2026-07-30T08:00:00+00:00",
      "AP8=",
    ]),
    row_count: 5000,
    truncated: true,
    duration_ms: 42,
  };
}

test("renders only a virtual window while preserving positional columns", () => {
  const wrapper = mount(QueryResultTable, {
    props: { result: largeResult() },
  });

  const renderedRows = wrapper.findAll('[data-result-row]');
  expect(renderedRows.length).toBeGreaterThan(0);
  expect(renderedRows.length).toBeLessThan(100);
  expect(
    wrapper.findAll('[role="columnheader"][data-column-index="0"]')[0]
      ?.find("strong")
      .text(),
  ).toBe("value");
  expect(
    wrapper.findAll('[role="columnheader"][data-column-index="1"]')[0]
      ?.find("strong")
      .text(),
  ).toBe("value");
  expect(renderedRows[0]?.findAll('[role="cell"]')[0]?.text()).toBe("row-0");
  expect(renderedRows[0]?.findAll('[role="cell"]')[1]?.text()).toBe(
    "9007199254740992",
  );
  expect(renderedRows[0]?.findAll('[role="cell"]')[2]?.text()).toBe("—");
  expect(renderedRows[0]?.text()).toContain("2026-07-30T08:00:00+00:00");
  expect(renderedRows[0]?.text()).toContain("AP8=");
  expect(wrapper.get('[data-result-scroll]').classes()).toContain(
    "query-result-scroll",
  );
});

test("makes truncation explicit", () => {
  const wrapper = mount(QueryResultTable, {
    props: { result: largeResult() },
  });

  expect(wrapper.get('[data-truncated-warning]').text()).toContain(
    "结果已截断",
  );
  expect(wrapper.text()).toContain("5,000");
});
