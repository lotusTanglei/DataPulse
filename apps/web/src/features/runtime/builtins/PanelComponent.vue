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

const title = computed(() => stringProp(props.instance.props, "title"));
const subtitle = computed(() => stringProp(props.instance.props, "subtitle"));
const frame = computed(() => stringProp(props.instance.props, "frame_variant", "tech"));
const showGrid = computed(() => props.instance.props?.show_grid !== false);
</script>

<template>
  <section class="screen-panel" :class="`screen-panel--${frame}`">
    <header v-if="title || subtitle" class="screen-panel__header">
      <div>
        <strong>{{ title }}</strong>
        <span v-if="subtitle">{{ subtitle }}</span>
      </div>
      <i v-if="frame !== 'plain'" aria-hidden="true"></i>
    </header>
    <div v-if="showGrid" class="screen-panel__grid" aria-hidden="true"></div>
  </section>
</template>

<style scoped>
.screen-panel {
  position: relative;
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border: 1px solid var(--screen-panel-border, #1b4160);
  border-radius: var(--screen-panel-radius, 4px);
  background: var(--screen-panel-background, rgb(11 27 43 / 88%));
  color: var(--screen-text-primary, #edf7ff);
}

.screen-panel--plain {
  border-color: var(--screen-panel-border, rgb(27 65 96 / 72%));
  background: var(--screen-panel-background, rgb(11 27 43 / 72%));
}

.screen-panel--corner::before,
.screen-panel--corner::after,
.screen-panel--tech::before,
.screen-panel--tech::after {
  position: absolute;
  width: 22px;
  height: 8px;
  border-top: 2px solid var(--screen-accent, #26d9c1);
  content: "";
}

.screen-panel--corner::before,
.screen-panel--tech::before {
  top: -1px;
  left: 12px;
  border-left: 2px solid var(--screen-accent, #26d9c1);
}

.screen-panel--corner::after,
.screen-panel--tech::after {
  right: 12px;
  bottom: -1px;
  border-right: 2px solid var(--screen-accent, #26d9c1);
  border-top: 0;
  border-bottom: 2px solid var(--screen-accent, #26d9c1);
}

.screen-panel--glass {
  background: rgb(16 37 58 / 52%);
  backdrop-filter: blur(8px);
}

.screen-panel__header {
  position: relative;
  z-index: 1;
  display: flex;
  min-height: 38px;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
  border-bottom: 1px solid var(--screen-panel-border, rgb(27 65 96 / 72%));
  background: linear-gradient(90deg, rgb(38 217 193 / 12%), transparent 72%);
}

.screen-panel__header div {
  display: grid;
  gap: 3px;
}

.screen-panel__header strong {
  font-size: 14px;
  font-weight: 600;
}

.screen-panel__header span {
  color: var(--screen-text-secondary, #9ab3c8);
  font-size: 10px;
}

.screen-panel__header i {
  width: 34px;
  height: 1px;
  background: var(--screen-accent, #26d9c1);
  opacity: 0.8;
}

.screen-panel__grid {
  position: absolute;
  inset: 38px 0 0;
  opacity: 0.12;
  background-image:
    linear-gradient(var(--screen-panel-border, #1b4160) 1px, transparent 1px),
    linear-gradient(90deg, var(--screen-panel-border, #1b4160) 1px, transparent 1px);
  background-size: 24px 24px;
  pointer-events: none;
}
</style>
