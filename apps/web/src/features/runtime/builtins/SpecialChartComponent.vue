<script setup lang="ts">
import { TitleComponent, TooltipComponent } from "echarts/components";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { computed, onMounted, ref } from "vue";
import VChart from "vue-echarts";

import type { QueryResult } from "../../query/types";
import type { ComponentInstance, LoadAsset } from "../types";
import { numericValue, stringProp } from "./format";

use([CanvasRenderer, TitleComponent, TooltipComponent]);

const pluginReady = ref(false);
const pluginError = ref(false);

onMounted(async () => {
  try {
    await Promise.all([
      import("echarts-liquidfill/index.js"),
      import("echarts-wordcloud/index.js"),
    ]);
    pluginReady.value = true;
  } catch {
    pluginError.value = true;
  }
});

const props = defineProps<{
  instance: ComponentInstance;
  result: QueryResult | null;
  loading: boolean;
  error: unknown | null;
  loadAsset: LoadAsset;
  theme?: Record<string, unknown>;
}>();

const emptyText = computed(() => stringProp(props.instance.props, "empty_text", "暂无数据"));
const option = computed(() => {
  const title = stringProp(props.instance.props, "title");
  const textColor = typeof props.theme?.text_primary === "string"
    ? props.theme.text_primary
    : "#eaf4ff";
  const common = {
    title: title
      ? { text: title, left: 14, top: 12, textStyle: { color: textColor, fontSize: 14 } }
      : undefined,
    tooltip: { show: true, confine: true },
  };
  if (props.instance.type === "builtin.liquid_fill") {
    const raw = numericValue(props.result?.rows[0]?.[0]) ?? 0;
    const value = Math.max(0, Math.min(1, raw > 1 ? raw / 100 : raw));
    return {
      ...common,
      series: [{
        type: "liquidFill",
        radius: "68%",
        center: ["50%", "55%"],
        data: [value, Math.max(0, value - 0.08)],
        label: { formatter: `${Math.round(value * 100)}%`, color: textColor, fontSize: 26 },
        outline: { borderDistance: 4, itemStyle: { borderWidth: 2, borderColor: "#26d9c1" } },
        backgroundStyle: { color: "rgba(38, 217, 193, 0.08)" },
      }],
    };
  }
  return {
    ...common,
    series: [{
      type: "wordCloud",
      shape: "circle",
      left: "center",
      top: title ? 48 : 12,
      width: "92%",
      height: title ? "78%" : "90%",
      sizeRange: [12, 42],
      rotationRange: [-30, 30],
      gridSize: 6,
      data: (props.result?.rows ?? []).map((row, index) => ({
        name: String(row[0] ?? ""),
        value: numericValue(row[1]) ?? 1,
        textStyle: { color: ["#26d9c1", "#4da3ff", "#f3b638", "#f16d75"][index % 4] },
      })),
    }],
  };
});
</script>

<template>
  <div class="special-chart">
    <p v-if="error || pluginError" role="status">图表加载失败</p>
    <p v-else-if="loading || !pluginReady" role="status">正在加载…</p>
    <p v-else-if="!result || result.rows.length === 0" role="status">{{ emptyText }}</p>
    <VChart v-else class="special-chart__canvas" :option="option" autoresize />
  </div>
</template>

<style scoped>
.special-chart { display: grid; width: 100%; height: 100%; min-height: 0; place-items: center; color: var(--screen-text-primary, #eaf4ff); }
.special-chart__canvas { width: 100%; height: 100%; min-height: 0; }
.special-chart p { margin: 0; color: var(--screen-text-secondary, #94a3b8); font-size: 13px; }
</style>
