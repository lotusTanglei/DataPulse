<script setup lang="ts">
import { computed } from "vue";

import type { QueryResult } from "../../query/types";
import type { ComponentInstance, LoadAsset } from "../types";
import { firstValue, formatNumber, numberProp, numericValue, stringProp } from "./format";

const props = defineProps<{
  instance: ComponentInstance;
  result: QueryResult | null;
  loading: boolean;
  error: unknown | null;
  loadAsset: LoadAsset;
}>();

const label = computed(() => stringProp(props.instance.props, "label", "核心指标"));
const unit = computed(() => stringProp(props.instance.props, "unit"));
const prefix = computed(() => stringProp(props.instance.props, "prefix"));
const value = computed(() => numericValue(firstValue(props.result)));
const formatted = computed(() => value.value === null ? "--" : `${prefix.value}${formatNumber(value.value, numberProp(props.instance.props, "precision", 0, { min: 0, max: 4 }))}`);
</script>

<template>
  <section class="screen-digital-number">
    <span>{{ label }}</span>
    <strong v-if="!error && !loading">{{ formatted }}<small v-if="unit">{{ unit }}</small></strong>
    <em v-else>{{ loading ? "..." : "--" }}</em>
    <i aria-hidden="true"></i>
  </section>
</template>

<style scoped>
.screen-digital-number {
  position: relative;
  container-type: inline-size;
  display: grid;
  align-content: center;
  width: 100%;
  height: 100%;
  gap: 8px;
  padding: 14px 18px;
  overflow: hidden;
  border-left: 3px solid var(--screen-accent, #26d9c1);
  background: linear-gradient(90deg, rgb(38 217 193 / 12%), transparent 72%);
  color: var(--screen-text-primary, #edf7ff);
}

.screen-digital-number > span {
  color: var(--screen-text-secondary, #9ab3c8);
  font-size: 12px;
}

.screen-digital-number strong,
.screen-digital-number em {
  color: var(--screen-accent, #26d9c1);
  font-family: "DIN Alternate", "Bahnschrift", Inter, sans-serif;
  font-size: clamp(28px, 18cqw, 58px);
  font-style: normal;
  font-weight: 600;
  letter-spacing: 0.03em;
  line-height: 1;
}

.screen-digital-number small {
  margin-left: 6px;
  color: var(--screen-text-secondary, #9ab3c8);
  font-family: inherit;
  font-size: 14px;
  letter-spacing: 0;
}

.screen-digital-number > i {
  position: absolute;
  right: 18px;
  bottom: 16px;
  width: 42px;
  height: 1px;
  background: var(--screen-accent, #26d9c1);
  opacity: 0.55;
}
</style>
