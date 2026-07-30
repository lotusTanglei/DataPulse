<script setup lang="ts">
import { computed } from "vue";

import type { QueryResult } from "../../query/types";
import type { ComponentInstance, LoadAsset } from "../types";
import {
  clamp,
  firstValue,
  formatNumber,
  numberProp,
  numericValue,
  stringProp,
} from "./format";

const props = defineProps<{
  instance: ComponentInstance;
  result: QueryResult | null;
  loading: boolean;
  error: unknown | null;
  loadAsset: LoadAsset;
}>();

const label = computed(() =>
  stringProp(props.instance.props, "label", "进度"),
);
const emptyText = computed(() =>
  stringProp(props.instance.props, "empty_text", "暂无数据"),
);
const rawValue = computed(() => numericValue(firstValue(props.result)));
const percentage = computed(() =>
  rawValue.value === null ? null : clamp(rawValue.value, 0, 100),
);
const formattedValue = computed(() => {
  if (percentage.value === null) {
    return "";
  }
  const precision = numberProp(props.instance.props, "precision", 0, {
    min: 0,
    max: 4,
  });
  return `${formatNumber(percentage.value, precision)}%`;
});
</script>

<template>
  <section class="screen-progress">
    <header>
      <span>{{ label }}</span>
      <strong v-if="percentage !== null">{{ formattedValue }}</strong>
    </header>
    <p v-if="error" class="screen-component-state" role="status">
      数据加载失败
    </p>
    <p v-else-if="loading" class="screen-component-state" role="status">
      正在加载…
    </p>
    <p
      v-else-if="percentage === null"
      class="screen-component-state"
      role="status"
    >
      {{ emptyText }}
    </p>
    <div
      v-else
      class="screen-progress__track"
      role="progressbar"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-valuenow="percentage"
      :aria-label="label"
    >
      <div
        class="screen-progress__value"
        :style="{ width: `${percentage}%` }"
      />
    </div>
  </section>
</template>

<style scoped>
.screen-progress {
  box-sizing: border-box;
  display: flex;
  width: 100%;
  height: 100%;
  flex-direction: column;
  justify-content: center;
  padding: 16px 18px;
  border: 1px solid var(--screen-component-border, transparent);
  border-radius: var(--screen-component-radius, 10px);
  background: var(--screen-component-surface, transparent);
  color: var(--screen-text-primary, #f8fafc);
}

.screen-progress header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.screen-progress header span {
  color: var(--screen-text-secondary, #94a3b8);
  font-size: 14px;
}

.screen-progress header strong {
  font-variant-numeric: tabular-nums;
}

.screen-progress__track {
  height: 10px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--screen-progress-track, rgb(148 163 184 / 20%));
}

.screen-progress__value {
  height: 100%;
  border-radius: inherit;
  background: var(--screen-accent, #3b82f6);
  transition: width 180ms ease;
}

.screen-component-state {
  margin: 0;
  color: var(--screen-text-secondary, #94a3b8);
  font-size: 13px;
}
</style>
