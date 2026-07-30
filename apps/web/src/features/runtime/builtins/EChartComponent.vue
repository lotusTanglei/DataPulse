<script setup lang="ts">
import { BarChart, LineChart, PieChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
} from "echarts/components";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import type { ECElementEvent } from "echarts/core";
import { computed } from "vue";
import VChart from "vue-echarts";

import type { JsonValue, QueryResult } from "../../query/types";
import type {
  ComponentInstance,
  LoadAsset,
  RuntimeInteraction,
} from "../types";
import { buildChartOption, type ChartTheme } from "./chartOptions";
import { stringProp } from "./format";

use([
  BarChart,
  CanvasRenderer,
  GridComponent,
  LegendComponent,
  LineChart,
  PieChart,
  TitleComponent,
  TooltipComponent,
]);

const props = defineProps<{
  instance: ComponentInstance;
  result: QueryResult | null;
  loading: boolean;
  error: unknown | null;
  loadAsset: LoadAsset;
  theme?: ChartTheme;
}>();

const emit = defineEmits<{
  interaction: [interaction: RuntimeInteraction];
}>();

const emptyText = computed(() =>
  stringProp(props.instance.props, "empty_text", "暂无数据"),
);
const option = computed(() =>
  props.result
    ? buildChartOption(props.instance, props.result, props.theme ?? {})
    : {},
);

function rowFromClick(event: ECElementEvent): Record<string, JsonValue> {
  const data = event.data;
  if (
    data !== null &&
    typeof data === "object" &&
    "__row" in data &&
    data.__row !== null &&
    typeof data.__row === "object" &&
    !Array.isArray(data.__row)
  ) {
    return data.__row as unknown as Record<string, JsonValue>;
  }
  const row = props.result?.rows[event.dataIndex ?? -1];
  return Object.fromEntries(
    (props.result?.columns ?? []).map((column, index) => [
      column.name,
      row?.[index] ?? null,
    ]),
  );
}

function handleClick(event: ECElementEvent): void {
  const row = rowFromClick(event);
  for (const interaction of props.instance.interactions ?? []) {
    const value = row[interaction.field];
    if (value !== undefined) {
      emit("interaction", {
        type: "set_parameter",
        name: interaction.parameter,
        value,
      });
    }
  }
}
</script>

<template>
  <div class="screen-chart">
    <p v-if="error" class="screen-component-state" role="status">
      数据加载失败
    </p>
    <p v-else-if="loading" class="screen-component-state" role="status">
      正在加载…
    </p>
    <p
      v-else-if="!result || result.rows.length === 0"
      class="screen-component-state"
      role="status"
    >
      {{ emptyText }}
    </p>
    <VChart
      v-else
      class="screen-chart__canvas"
      :option="option"
      autoresize
      @click="handleClick"
    />
  </div>
</template>

<style scoped>
.screen-chart {
  display: grid;
  width: 100%;
  height: 100%;
  min-height: 0;
  place-items: center;
  color: var(--screen-text-primary, #f8fafc);
}

.screen-chart__canvas {
  width: 100%;
  height: 100%;
  min-height: 0;
}

.screen-component-state {
  margin: 0;
  color: var(--screen-text-secondary, #94a3b8);
  font-size: 13px;
}
</style>
