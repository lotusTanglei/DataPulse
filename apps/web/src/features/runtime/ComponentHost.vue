<script setup lang="ts">
import { computed, onErrorCaptured, ref, watch } from "vue";

import type { JsonValue } from "../query/types";
import type {
  ComponentDefinition,
  ComponentInstance,
  ComponentQueryState,
  LoadAsset,
  RuntimeInteraction,
  RuntimeMode,
} from "./types";
import { resolveTheme } from "./theme";

const props = defineProps<{
  definition?: ComponentDefinition;
  instance: ComponentInstance;
  loadAsset: LoadAsset;
  queryState: ComponentQueryState;
  theme: Record<string, JsonValue>;
  mode?: RuntimeMode;
}>();

const emit = defineEmits<{
  interaction: [interaction: RuntimeInteraction];
}>();

function stringStyle(name: string): string | undefined {
  const value = props.instance.style?.[name] ?? props.definition?.defaultStyle?.[name];
  return typeof value === "string" && value.trim() ? value : undefined;
}

function numberStyle(name: string): number | undefined {
  const value = props.instance.style?.[name] ?? props.definition?.defaultStyle?.[name];
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

const hostStyle = computed(() => {
  const borderWidth = Math.max(0, numberStyle("border_width") ?? 0);
  const opacity = Math.min(1, Math.max(0, numberStyle("opacity") ?? 1));
  const radius = Math.max(0, numberStyle("border_radius") ?? 0);
  const surface = stringStyle("background_color");
  const borderColor = stringStyle("border_color");
  return {
    ...resolveTheme({ tokens: props.theme }),
    "--screen-component-surface": surface,
    "--screen-component-border": borderColor,
    "--screen-component-radius": `${radius}px`,
    backgroundColor: surface,
    color: stringStyle("text_color"),
    border: borderWidth > 0
      ? `${borderWidth}px solid ${borderColor ?? "currentColor"}`
      : undefined,
    borderRadius: `${radius}px`,
    opacity,
  };
});

const sourceLabel = computed(() => {
  if (props.mode !== "editor" && props.mode !== "preview") {
    return "";
  }
  const source = props.instance.data_binding?.source;
  return source === "mock" ? "演示数据" : source === "static" ? "固定数据" : "";
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
    <span v-if="sourceLabel" class="component-host__source-badge">{{ sourceLabel }}</span>
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
  position: relative;
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.component-host__source-badge {
  position: absolute;
  z-index: 8;
  top: 6px;
  right: 6px;
  padding: 2px 5px;
  border: 1px solid color-mix(in srgb, var(--screen-accent, #26d9c1) 40%, transparent);
  border-radius: 3px;
  color: var(--screen-accent, #26d9c1);
  background: color-mix(in srgb, var(--screen-panel-background-alt, #10253a) 88%, transparent);
  font-size: 9px;
  line-height: 1.2;
  pointer-events: none;
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
