<script setup lang="ts">
import { computed, type CSSProperties } from "vue";

import type { QueryResult } from "../../query/types";
import type { ComponentInstance, LoadAsset } from "../types";
import { numberProp, stringProp } from "./format";

const props = defineProps<{
  instance: ComponentInstance;
  result: QueryResult | null;
  loading: boolean;
  error: unknown | null;
  loadAsset: LoadAsset;
}>();

const text = computed(() => stringProp(props.instance.props, "text", "文本"));
const alignment = computed(() => {
  const value = stringProp(props.instance.props, "align", "left");
  return ["left", "center", "right"].includes(value) ? value : "left";
});
const fontSize = computed(() =>
  numberProp(props.instance.props, "font_size", 24, { min: 10, max: 160 }),
);
const fontWeight = computed(() =>
  numberProp(props.instance.props, "font_weight", 500, {
    min: 100,
    max: 900,
  }),
);
const textStyle = computed<CSSProperties>(() => ({
  fontSize: `${fontSize.value}px`,
  fontWeight: fontWeight.value,
  textAlign: alignment.value as CSSProperties["textAlign"],
}));
</script>

<template>
  <div class="screen-text" :style="textStyle">
    {{ text }}
  </div>
</template>

<style scoped>
.screen-text {
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  overflow: hidden;
  color: var(--screen-text-primary, #f8fafc);
  line-height: 1.35;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
</style>
