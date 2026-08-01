<script setup lang="ts">
import { computed } from "vue";

import type { ChartSpec } from "../../contracts";
import type { JsonValue } from "../query/types";
import ComponentHost from "../runtime/ComponentHost.vue";
import { defaultComponentRegistry } from "../runtime/registry";
import type { ComponentQueryState } from "../runtime/types";
import { createChartSuggestionPreviewInstance } from "../screens/editor/chartSuggestion";
import type { AiChartResponse } from "./types";

const props = withDefaults(
  defineProps<{
    response: AiChartResponse;
    currentProps?: Record<string, JsonValue>;
    applyLabel?: string;
    canApply?: boolean;
  }>(),
  {
    currentProps: undefined,
    applyLabel: "应用图表建议",
    canApply: false,
  },
);

const emit = defineEmits<{
  "apply-chart": [chartSpec: ChartSpec];
}>();

const previewInstance = computed(() =>
  createChartSuggestionPreviewInstance(
    props.response.chart_spec,
    props.currentProps,
  ),
);
const definition = computed(() =>
  defaultComponentRegistry.get(previewInstance.value.type),
);
const previewState = computed<ComponentQueryState>(() => ({
  status: "success",
  result: props.response.preview,
  error: null,
}));
const theme = {
  text_primary: "#e2e8f0",
  text_secondary: "#94a3b8",
  component_border: "#334155",
  component_surface: "#0f172a",
  chart_colors: ["#3b82f6", "#22c55e", "#f59e0b", "#a855f7"],
};

async function loadAsset(): Promise<string> {
  return "";
}
</script>

<template>
  <article class="ai-chart-card">
    <header class="ai-chart-card__header">
      <div>
        <p class="ai-chart-card__eyebrow">AI 图表建议</p>
        <h3>{{ response.chart_spec.visual.title || "推荐图表" }}</h3>
      </div>
      <button
        v-if="canApply"
        class="secondary-button"
        type="button"
        @click="emit('apply-chart', response.chart_spec)"
      >
        {{ applyLabel }}
      </button>
    </header>

    <p class="ai-chart-card__explanation">
      {{ response.explanation }}
    </p>

    <div class="ai-chart-card__meta">
      <span>图表类型 {{ response.chart_spec.visual.type }}</span>
      <span>预览 {{ response.preview.row_count.toLocaleString("zh-CN") }} 行</span>
      <span>
        字段
        {{
          (response.chart_spec.dimensions?.length ?? 0) +
          (response.chart_spec.measures?.length ?? 0)
        }}
      </span>
    </div>

    <ul
      v-if="response.warnings.length > 0"
      class="ai-chart-card__warnings"
      aria-label="AI 警告"
    >
      <li v-for="warning in response.warnings" :key="warning">
        {{ warning }}
      </li>
    </ul>

    <div class="ai-chart-card__preview">
      <ComponentHost
        :definition="definition"
        :instance="previewInstance"
        :load-asset="loadAsset"
        :query-state="previewState"
        :theme="theme"
      />
    </div>
  </article>
</template>

<style scoped>
.ai-chart-card {
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid rgb(148 163 184 / 20%);
  border-radius: 16px;
  background: rgb(15 23 42 / 65%);
}

.ai-chart-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.ai-chart-card__header h3,
.ai-chart-card__explanation,
.ai-chart-card__warnings {
  margin: 0;
}

.ai-chart-card__eyebrow {
  margin: 0 0 4px;
  color: rgb(148 163 184);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.ai-chart-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: rgb(148 163 184);
  font-size: 12px;
}

.ai-chart-card__meta span,
.ai-chart-card__warnings li {
  padding: 4px 8px;
  border-radius: 999px;
  background: rgb(30 41 59 / 75%);
}

.ai-chart-card__warnings {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0;
  list-style: none;
}

.ai-chart-card__preview {
  min-height: 280px;
  padding: 12px;
  border-radius: 12px;
  background: rgb(2 6 23 / 80%);
}
</style>
