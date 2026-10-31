<script setup lang="ts">
import {
  BarChart,
  GraphChart,
  HeatmapChart,
  SankeyChart,
} from "echarts/charts";
import {
  CalendarComponent,
  PolarComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
} from "echarts/components";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { computed } from "vue";
import VChart from "vue-echarts";

import type { QueryResult } from "../../query/types";
import type { ComponentInstance, LoadAsset } from "../types";
import { applyChartMotionPreference } from "./chartMotion";
import { buildAdvancedChartOption } from "./advancedChartOptions";
import { stringProp } from "./format";

use([
  BarChart,
  CalendarComponent,
  CanvasRenderer,
  GraphChart,
  HeatmapChart,
  PolarComponent,
  SankeyChart,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
]);

const props = defineProps<{
  instance: ComponentInstance;
  result: QueryResult | null;
  loading: boolean;
  error: unknown | null;
  loadAsset: LoadAsset;
  theme?: Record<string, unknown>;
}>();

const emptyText = computed(() => stringProp(props.instance.props, "empty_text", "暂无数据"));
const option = computed(() =>
  props.result
    ? applyChartMotionPreference(
        buildAdvancedChartOption(props.instance, props.result, props.theme ?? {}),
      )
    : {},
);
</script>

<template>
  <div class="advanced-chart">
    <p v-if="error" role="status">数据加载失败</p>
    <p v-else-if="loading" role="status">正在加载…</p>
    <p v-else-if="!result || result.rows.length === 0" role="status">{{ emptyText }}</p>
    <VChart v-else class="advanced-chart__canvas" :option="option" autoresize />
  </div>
</template>

<style scoped>
.advanced-chart { display: grid; width: 100%; height: 100%; min-height: 0; place-items: center; color: var(--screen-text-primary, #eaf4ff); }
.advanced-chart__canvas { width: 100%; height: 100%; min-height: 0; }
.advanced-chart p { margin: 0; color: var(--screen-text-secondary, #94a3b8); font-size: 13px; }
</style>
