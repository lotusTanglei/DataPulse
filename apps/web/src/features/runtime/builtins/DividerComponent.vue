<script setup lang="ts">
import { computed } from "vue";

import type { ComponentInstance, LoadAsset } from "../types";
import { stringProp } from "./format";

const props = defineProps<{
  instance: ComponentInstance;
  result: null;
  loading: boolean;
  error: unknown | null;
  loadAsset: LoadAsset;
}>();

const orientation = computed(() => stringProp(props.instance.props, "orientation", "horizontal"));
const label = computed(() => stringProp(props.instance.props, "label"));
</script>

<template>
  <div class="screen-divider" :class="`screen-divider--${orientation}`">
    <span v-if="label">{{ label }}</span>
  </div>
</template>

<style scoped>
.screen-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--screen-text-muted, #638198);
  font-size: 11px;
}

.screen-divider::before,
.screen-divider::after {
  display: block;
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--screen-panel-border, #1b4160));
  content: "";
}

.screen-divider::after {
  transform: scaleX(-1);
}

.screen-divider span {
  padding: 0 12px;
}

.screen-divider--vertical {
  flex-direction: column;
}

.screen-divider--vertical::before,
.screen-divider--vertical::after {
  width: 1px;
  height: auto;
  min-height: 20px;
  flex: 1;
  background: linear-gradient(180deg, transparent, var(--screen-panel-border, #1b4160));
}

.screen-divider--vertical::after {
  transform: scaleY(-1);
}
</style>
