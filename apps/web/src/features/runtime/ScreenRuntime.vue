<script setup lang="ts">
import {
  computed,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";

import type { DashboardDocument } from "../../contracts";
import type { JsonValue } from "../query/types";
import ComponentHost from "./ComponentHost.vue";
import { createDataRuntime } from "./dataRuntime";
import {
  createParameterState,
  type ParameterMutationSource,
} from "./parameters";
import {
  defaultComponentRegistry,
  type ComponentRegistry,
} from "./registry";
import { resolveTheme } from "./theme";
import type {
  LoadAsset,
  QueryComponent,
  RuntimeInteraction,
  RuntimeMode,
  RuntimeParameters,
} from "./types";

const props = withDefaults(
  defineProps<{
    document: DashboardDocument;
    initialParameters?: RuntimeParameters;
    loadAsset: LoadAsset;
    mode: RuntimeMode;
    queryComponent: QueryComponent;
    registry?: ComponentRegistry;
  }>(),
  {
    initialParameters: () => ({}),
    registry: () => defaultComponentRegistry,
  },
);

const emit = defineEmits<{
  error: [error: unknown];
  parametersChange: [parameters: RuntimeParameters];
}>();

const container = ref<HTMLElement | null>(null);
const scale = ref(1);
const parameterVersion = ref(0);
const dataRuntime = createDataRuntime(props.queryComponent);
let parameterState = createParameterState(
  props.document.parameters ?? [],
  props.initialParameters,
);
let refreshTimer: ReturnType<typeof setInterval> | null = null;
let resizeObserver: ResizeObserver | null = null;

const components = computed(() =>
  (props.document.components ?? []).filter(
    (component) => !component.state?.hidden,
  ),
);
const themeStyle = computed(() => resolveTheme(props.document.theme));
const themeTokens = computed(() => props.document.theme?.tokens ?? {});
const canvasStyle = computed(() => {
  const background = props.document.canvas.background;
  const color =
    background && typeof background.color === "string"
      ? background.color
      : "transparent";
  return {
    ...themeStyle.value,
    width: `${props.document.canvas.width}px`,
    height: `${props.document.canvas.height}px`,
    backgroundColor: color,
    transform: `scale(${scale.value})`,
  };
});
const viewportStyle = computed(() => ({
  width: `${props.document.canvas.width * scale.value}px`,
  height: `${props.document.canvas.height * scale.value}px`,
}));

function hasBinding(binding: unknown): binding is Record<string, JsonValue> {
  return (
    binding !== null &&
    typeof binding === "object" &&
    !Array.isArray(binding) &&
    Object.keys(binding).length > 0
  );
}

async function refresh(): Promise<void> {
  dataRuntime.beginGeneration();
  const parameters = parameterState.values();
  const loads = components.value
    .filter((component) => hasBinding(component.data_binding))
    .map((component) =>
      dataRuntime
        .load(component.id, component.data_binding!, parameters)
        .catch((error: unknown) => {
          emit("error", error);
        }),
    );
  await Promise.all(loads);
}

function setParameter(
  name: string,
  value: JsonValue,
  source: ParameterMutationSource = "runtime",
): void {
  parameterState.set(name, value, source);
  parameterVersion.value += 1;
  const parameters = parameterState.values();
  emit("parametersChange", parameters);
  void refresh();
}

function handleInteraction(interaction: RuntimeInteraction): void {
  setParameter(interaction.name, interaction.value);
}

function updateScale(): void {
  const host = container.value;
  if (!host) {
    return;
  }
  const widthScale = host.clientWidth / props.document.canvas.width;
  const heightScale =
    host.clientHeight > 0
      ? host.clientHeight / props.document.canvas.height
      : widthScale;
  const nextScale = Math.min(widthScale, heightScale);
  scale.value = Number.isFinite(nextScale) && nextScale > 0 ? nextScale : 1;
}

function configureTimer(): void {
  if (refreshTimer !== null) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
  const refreshPolicy = props.document.refresh;
  if (
    refreshPolicy?.mode === "interval" &&
    refreshPolicy.interval_seconds !== null &&
    refreshPolicy.interval_seconds !== undefined
  ) {
    refreshTimer = setInterval(
      () => void refresh(),
      refreshPolicy.interval_seconds * 1000,
    );
  }
}

watch(
  () => props.document,
  (document) => {
    parameterState = createParameterState(
      document.parameters ?? [],
      props.initialParameters,
    );
    parameterVersion.value += 1;
    configureTimer();
    updateScale();
    void refresh();
  },
);

onMounted(() => {
  resizeObserver =
    typeof ResizeObserver === "undefined"
      ? null
      : new ResizeObserver(updateScale);
  if (resizeObserver && container.value) {
    resizeObserver.observe(container.value);
  }
  window.addEventListener("resize", updateScale);
  updateScale();
  configureTimer();
  void refresh();
});

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  window.removeEventListener("resize", updateScale);
  if (refreshTimer !== null) {
    clearInterval(refreshTimer);
  }
  dataRuntime.dispose();
});

defineExpose({
  getParameters: () => parameterState.values(),
  refresh,
  setParameter,
});
</script>

<template>
  <div
    ref="container"
    class="screen-runtime"
    :data-mode="mode"
    :data-parameter-version="parameterVersion"
  >
    <div class="screen-runtime__viewport" :style="viewportStyle">
      <div class="screen-runtime__canvas" :style="canvasStyle">
        <ComponentHost
          v-for="component in components"
          :key="component.id"
          class="screen-runtime__component"
          :style="{
            left: `${component.frame.x}px`,
            top: `${component.frame.y}px`,
            width: `${component.frame.width}px`,
            height: `${component.frame.height}px`,
            zIndex: component.frame.z_index ?? 0,
          }"
          :definition="registry.get(component.type)"
          :instance="component"
          :load-asset="loadAsset"
          :query-state="dataRuntime.state(component.id)"
          :theme="themeTokens"
          @interaction="handleInteraction"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.screen-runtime {
  display: grid;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  place-items: center;
}

.screen-runtime__viewport {
  position: relative;
  flex: none;
}

.screen-runtime__canvas {
  position: absolute;
  inset: 0 auto auto 0;
  overflow: hidden;
  color: var(--dp-text, #f8fafc);
  font-family: var(
    --dp-font-family,
    Inter,
    ui-sans-serif,
    system-ui,
    sans-serif
  );
  transform-origin: top left;
}

.screen-runtime__component {
  position: absolute;
  box-sizing: border-box;
}
</style>
