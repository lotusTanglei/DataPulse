import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";

import type { QueryResult } from "../../query/types";
import { defaultComponentRegistry } from "../registry";
import AlertListComponent from "./AlertListComponent.vue";
import DigitalNumberComponent from "./DigitalNumberComponent.vue";
import DividerComponent from "./DividerComponent.vue";
import GaugeComponent from "./GaugeComponent.vue";
import ImageComponent from "./ImageComponent.vue";
import KpiComponent from "./KpiComponent.vue";
import PanelComponent from "./PanelComponent.vue";
import ProgressComponent from "./ProgressComponent.vue";
import RankingComponent from "./RankingComponent.vue";
import StatusMatrixComponent from "./StatusMatrixComponent.vue";
import TableComponent from "./TableComponent.vue";
import TextComponent from "./TextComponent.vue";
import TimelineComponent from "./TimelineComponent.vue";

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

test("new component definitions expose category, skin, and demo capability", () => {
  const definitions = defaultComponentRegistry.list();
  expect(definitions).toHaveLength(22);
  for (const definition of definitions) {
    expect(definition.category).toBeTruthy();
    expect(definition.defaultStyle).toBeTruthy();
    expect(definition.demoDataKind).toBeTruthy();
    expect(definition.propertyGroups?.length).toBeGreaterThan(0);
  }
  expect(
    definitions
      .filter((definition) => definition.dataCapability !== "none")
      .map((definition) => definition.type),
  ).toContain("builtin.ranking");
});

test("new visual components render their success states", () => {
  const loadAsset = vi.fn();
  const shared = {
    loading: false,
    error: null,
    loadAsset,
  };
  const wrappers = [
    mount(PanelComponent, {
      props: { instance: instance("builtin.panel", { title: "重点区域" }), result: null, ...shared },
    }),
    mount(DividerComponent, {
      props: { instance: instance("builtin.divider", { label: "分组" }), result: null, ...shared },
    }),
    mount(DigitalNumberComponent, {
      props: { instance: instance("builtin.digital_number", { label: "总量", unit: "项" }), result: result([[128]]), ...shared },
    }),
    mount(GaugeComponent, {
      props: { instance: instance("builtin.gauge", { label: "完成率" }), result: result([[76]]), ...shared },
    }),
    mount(RankingComponent, {
      props: { instance: instance("builtin.ranking"), result: result([["A", 12], ["B", 8]], [{ name: "名称", data_type: "text" }, { name: "值", data_type: "numeric" }]), ...shared },
    }),
    mount(AlertListComponent, {
      props: { instance: instance("builtin.alert_list"), result: result([["high", "需要处理", "说明", "08:30"]], [{ name: "level", data_type: "text" }, { name: "title", data_type: "text" }, { name: "detail", data_type: "text" }, { name: "time", data_type: "text" }]), ...shared },
    }),
    mount(StatusMatrixComponent, {
      props: { instance: instance("builtin.status_matrix"), result: result([["对象 A", "正常"]], [{ name: "name", data_type: "text" }, { name: "status", data_type: "text" }]), ...shared },
    }),
    mount(TimelineComponent, {
      props: { instance: instance("builtin.timeline"), result: result([["08:30", "事件 A", "完成"]], [{ name: "time", data_type: "text" }, { name: "title", data_type: "text" }, { name: "status", data_type: "text" }]), ...shared },
    }),
  ];

  expect(wrappers.map((wrapper) => wrapper.text())).toEqual(
    expect.arrayContaining([
      expect.stringContaining("重点区域"),
      expect.stringContaining("分组"),
      expect.stringContaining("128"),
      expect.stringContaining("76.0%"),
      expect.stringContaining("A"),
      expect.stringContaining("需要处理"),
      expect.stringContaining("对象 A"),
      expect.stringContaining("事件 A"),
    ]),
  );
  for (const wrapper of wrappers) wrapper.unmount();
});
