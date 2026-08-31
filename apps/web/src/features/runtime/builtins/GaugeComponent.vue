<script setup lang="ts">
import { computed } from "vue";

import type { QueryResult } from "../../query/types";
import type { ComponentInstance, LoadAsset } from "../types";
import { clamp, firstValue, formatNumber, numberProp, numericValue, stringProp } from "./format";

const props = defineProps<{
  instance: ComponentInstance;
  result: QueryResult | null;
  loading: boolean;
  error: unknown | null;
  loadAsset: LoadAsset;
}>();

const label = computed(() => stringProp(props.instance.props, "label", "完成率"));
const rawValue = computed(() => numericValue(firstValue(props.result)));
const value = computed(() => rawValue.value === null ? null : clamp(rawValue.value, 0, 100));
const precision = computed(() => numberProp(props.instance.props, "precision", 1, { min: 0, max: 3 }));
const ringStyle = computed(() => ({ background: `conic-gradient(var(--screen-accent, #26d9c1) 0 ${value.value ?? 0}%, var(--screen-panel-background-alt, #173149) ${value.value ?? 0}% 100%)` }));
</script>

<template>
  <section class="screen-gauge">
    <div v-if="value !== null && !loading && !error" class="screen-gauge__ring" :style="ringStyle">
      <div><strong>{{ formatNumber(value, precision) }}%</strong><span>{{ label }}</span></div>
    </div>
    <p v-else class="screen-component-state">{{ loading ? "正在加载…" : error ? "数据加载失败" : "暂无数据" }}</p>
  </section>
</template>

<style scoped>
.screen-gauge {
  container-type: inline-size;
  display: grid;
  width: 100%;
  height: 100%;
  place-items: center;
  color: var(--screen-text-primary, #edf7ff);
}

.screen-gauge__ring {
  position: relative;
  display: grid;
  width: min(74%, 172px);
  aspect-ratio: 1;
  place-items: center;
  border-radius: 50%;
  filter: drop-shadow(0 0 16px rgb(38 217 193 / 18%));
}

.screen-gauge__ring::before {
  position: absolute;
  width: calc(min(74%, 172px) - 22px);
  aspect-ratio: 1;
  border-radius: 50%;
  background: var(--screen-panel-background, #0b1b2b);
  content: "";
}

.screen-gauge__ring > div {
  z-index: 1;
  display: grid;
  gap: 5px;
  text-align: center;
}

.screen-gauge strong {
  font-size: clamp(24px, 10cqw, 40px);
  font-weight: 600;
}

.screen-gauge span {
  color: var(--screen-text-secondary, #9ab3c8);
  font-size: 11px;
}

.screen-component-state {
  margin: 0;
  color: var(--screen-text-secondary, #9ab3c8);
  font-size: 13px;
}
</style>
