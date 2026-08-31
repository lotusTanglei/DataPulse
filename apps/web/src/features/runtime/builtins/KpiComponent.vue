<script setup lang="ts">
import { computed } from "vue";

import type { QueryResult } from "../../query/types";
import type { ComponentInstance, LoadAsset } from "../types";
import {
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
  stringProp(props.instance.props, "label", "指标"),
);
const emptyText = computed(() =>
  stringProp(props.instance.props, "empty_text", "暂无数据"),
);
const value = computed(() => numericValue(firstValue(props.result)));
const formattedValue = computed(() => {
  if (value.value === null) {
    return "";
  }
  const precision = numberProp(props.instance.props, "precision", 0, {
    min: 0,
    max: 8,
  });
  const prefix = stringProp(props.instance.props, "prefix");
  const suffix = stringProp(props.instance.props, "suffix");
  return `${prefix}${formatNumber(value.value, precision)}${suffix}`;
});
</script>

<template>
  <section class="screen-kpi">
    <p class="screen-kpi__label">{{ label }}</p>
    <p v-if="error" class="screen-component-state" role="status">
      数据加载失败
    </p>
    <p v-else-if="loading" class="screen-component-state" role="status">
      正在加载…
    </p>
    <p v-else-if="value === null" class="screen-component-state" role="status">
      {{ emptyText }}
    </p>
    <strong v-else class="screen-kpi__value">{{ formattedValue }}</strong>
  </section>
</template>

<style scoped>
.screen-kpi {
  position: relative;
  box-sizing: border-box;
  container-type: inline-size;
  display: flex;
  width: 100%;
  height: 100%;
  flex-direction: column;
  justify-content: center;
  padding: 18px 20px;
  border: 1px solid var(--screen-component-border, transparent);
  border-radius: var(--screen-component-radius, 10px);
  background: var(--screen-component-surface, transparent);
  color: var(--screen-text-primary, #f8fafc);
}

.screen-kpi::before {
  position: absolute;
  top: 0;
  right: 18px;
  left: 18px;
  height: 2px;
  background: linear-gradient(90deg, var(--screen-accent, #26d9c1), transparent);
  content: "";
  opacity: 0.85;
}

.screen-kpi__label,
.screen-component-state {
  margin: 0;
  color: var(--screen-text-secondary, #94a3b8);
  font-size: 14px;
}

.screen-kpi__value {
  margin-top: 10px;
  font-size: clamp(24px, 10cqw, 48px);
  font-variant-numeric: tabular-nums;
  line-height: 1;
}
</style>
