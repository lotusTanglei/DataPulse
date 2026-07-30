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
  <div class="component-host" :data-component-id="instance.id">
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
