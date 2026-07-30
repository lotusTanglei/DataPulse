import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";

import type { QueryResult } from "../../query/types";
import { defaultComponentRegistry } from "../registry";
import ImageComponent from "./ImageComponent.vue";
import KpiComponent from "./KpiComponent.vue";
import ProgressComponent from "./ProgressComponent.vue";
import TableComponent from "./TableComponent.vue";
import TextComponent from "./TextComponent.vue";

function result(
  rows: QueryResult["rows"],
  columns: QueryResult["columns"] = [
    { name: "value", data_type: "numeric" },
  ],
): QueryResult {
  return {
    request_id: "component-query",
    columns,
    rows,
    row_count: rows.length,
    truncated: false,
    duration_ms: 4,
  };
}

function instance(
  type: string,
  props: Record<string, string | number | boolean | null> = {},
) {
  return {
    id: `${type}-1`,
    type,
    frame: { x: 0, y: 0, width: 320, height: 160 },
    props,
  };
}

afterEach(() => {
  vi.restoreAllMocks();
});

test("text renders document text as escaped content", () => {
  const wrapper = mount(TextComponent, {
    props: {
      instance: instance("builtin.text", {
        text: '<img src=x onerror="alert(1)">运营概览',
      }),
      result: null,
      loading: false,
      error: null,
      loadAsset: vi.fn(),
    },
  });

  expect(wrapper.text()).toContain('<img src=x onerror="alert(1)">运营概览');
  expect(wrapper.find("img").exists()).toBe(false);
});

test("image loads only its asset id and revokes a returned object URL", async () => {
  const revoke = vi
    .spyOn(URL, "revokeObjectURL")
    .mockImplementation(() => undefined);
  const loadAsset = vi.fn().mockResolvedValue("blob:datapulse/image-1");
  const wrapper = mount(ImageComponent, {
    props: {
      instance: instance("builtin.image", {
        asset_id: "image-1",
        alt: "门店照片",
        fit: "contain",
      }),
      result: null,
      loading: false,
      error: null,
      loadAsset,
    },
  });

  await flushPromises();

  expect(loadAsset).toHaveBeenCalledWith("image-1", expect.any(AbortSignal));
  expect(wrapper.get("img").attributes()).toMatchObject({
    alt: "门店照片",
    src: "blob:datapulse/image-1",
  });
  wrapper.unmount();
  expect(revoke).toHaveBeenCalledWith("blob:datapulse/image-1");
});

test("KPI formats the first measure and exposes safe runtime states", async () => {
  const wrapper = mount(KpiComponent, {
    props: {
      instance: instance("builtin.kpi", {
        label: "销售额",
        precision: 2,
        prefix: "¥",
        empty_text: "等待数据",
      }),
      result: result([["1250.5"]]),
      loading: false,
      error: null,
      loadAsset: vi.fn(),
    },
  });

  expect(wrapper.text()).toContain("销售额");
  expect(wrapper.text()).toContain("¥1,250.50");

  await wrapper.setProps({ loading: true });
  expect(wrapper.get('[role="status"]').text()).toContain("正在加载");
  await wrapper.setProps({ loading: false, result: result([]) });
  expect(wrapper.get('[role="status"]').text()).toBe("等待数据");
  await wrapper.setProps({
    error: new Error("password=do-not-leak"),
    result: null,
  });
  expect(wrapper.get('[role="status"]').text()).toBe("数据加载失败");
  expect(wrapper.text()).not.toContain("do-not-leak");
});

test("table preserves positional columns and rows", () => {
  const wrapper = mount(TableComponent, {
    props: {
      instance: instance("builtin.table"),
      result: result(
        [
          ["华东", "1200.5", null],
          ["华南", "980", "正常"],
        ],
        [
          { name: "区域", data_type: "text" },
          { name: "销售额", data_type: "numeric" },
          { name: "状态", data_type: "text" },
        ],
      ),
      loading: false,
      error: null,
      loadAsset: vi.fn(),
    },
  });

  expect(wrapper.findAll("th").map((cell) => cell.text())).toEqual([
    "区域",
    "销售额",
    "状态",
  ]);
  expect(
    wrapper
      .findAll("tbody tr")[0]
      ?.findAll("td")
      .map((cell) => cell.text()),
  ).toEqual(["华东", "1200.5", "—"]);
});

test("progress clamps values and renders a bounded visual percentage", () => {
  const wrapper = mount(ProgressComponent, {
    props: {
      instance: instance("builtin.progress", {
        label: "目标完成率",
        precision: 1,
      }),
      result: result([[135.25]]),
      loading: false,
      error: null,
      loadAsset: vi.fn(),
    },
  });

  expect(wrapper.text()).toContain("目标完成率");
  expect(wrapper.text()).toContain("100.0%");
  expect(wrapper.get('[role="progressbar"]').attributes()).toMatchObject({
    "aria-valuemin": "0",
    "aria-valuemax": "100",
    "aria-valuenow": "100",
  });
  expect(
    wrapper.get(".screen-progress__value").attributes("style"),
  ).toContain("width: 100%");
});

test("registers all core component types in the shared registry", () => {
  expect(
    [
      "builtin.text",
      "builtin.image",
      "builtin.kpi",
      "builtin.table",
      "builtin.progress",
    ].map((type) => defaultComponentRegistry.get(type)?.label),
  ).toEqual(["文本", "图片", "指标", "表格", "进度"]);
});
