<script setup lang="ts">
import { computed, onErrorCaptured, ref, watch } from "vue";

import type { JsonValue } from "../query/types";
import type {
  ComponentDefinition,
  ComponentInstance,
  ComponentQueryState,
  LoadAsset,
  RuntimeInteraction,
} from "./types";

const props = defineProps<{
  definition?: ComponentDefinition;
  instance: ComponentInstance;
  loadAsset: LoadAsset;
  queryState: ComponentQueryState;
  theme: Record<string, JsonValue>;
}>();

const emit = defineEmits<{
  interaction: [interaction: RuntimeInteraction];
}>();

function stringStyle(name: string): string | undefined {
  const value = props.instance.style?.[name];
  return typeof value === "string" && value.trim() ? value : undefined;
}

function numberStyle(name: string): number | undefined {
  const value = props.instance.style?.[name];
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

const hostStyle = computed(() => {
  const borderWidth = Math.max(0, numberStyle("border_width") ?? 0);
  const opacity = Math.min(1, Math.max(0, numberStyle("opacity") ?? 1));
  return {
    backgroundColor: stringStyle("background_color"),
    color: stringStyle("text_color"),
    border: borderWidth > 0
      ? `${borderWidth}px solid ${stringStyle("border_color") ?? "currentColor"}`
      : undefined,
    borderRadius: `${Math.max(0, numberStyle("border_radius") ?? 0)}px`,
    opacity,
  };
});

const renderFailed = ref(false);
const errorMessage = computed(() => {
  if (!props.definition) {
    return `暂不支持组件类型：${props.instance.type}`;
  }
  if (renderFailed.value) {
    return "组件渲染失败";
  }
  return "";
});

watch(
  () => [props.instance.id, props.instance.type],
  () => {
    renderFailed.value = false;
  },
);

onErrorCaptured(() => {
  renderFailed.value = true;
  return false;
});
</script>

<template>
  <div class="component-host" :data-component-id="instance.id" :style="hostStyle">
    <div v-if="errorMessage" class="component-host__fallback" role="status">
      {{ errorMessage }}
    </div>
    <component
      :is="definition.component"
      v-else-if="definition"
      :instance="instance"
      :result="queryState.result"
      :loading="queryState.status === 'loading'"
      :error="queryState.error"
      :load-asset="loadAsset"
      v-bind="
        definition.dataCapability === 'series' ||
        definition.dataCapability === 'geo'
          ? { theme }
          : {}
      "
      @interaction="emit('interaction', $event)"
    />
  </div>
</template>

<style scoped>
.component-host {
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.component-host__fallback {
  box-sizing: border-box;
  display: grid;
  width: 100%;
  height: 100%;
  min-height: 48px;
  place-items: center;
  padding: 12px;
  border: 1px dashed color-mix(in srgb, currentColor 25%, transparent);
  border-radius: 6px;
  color: color-mix(in srgb, currentColor 58%, transparent);
  font-size: 12px;
  text-align: center;
}
</style>
