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
import { resolveTheme, resolveThemeTokens } from "./theme";
import type {
  LoadAsset,
  QueryComponent,
  RuntimeInteraction,
  RuntimeMode,
  RuntimeParameters,
} from "./types";
import { resolveRuntimeViewport } from "./viewport";
import type { SpeechCommand, SpeechEvent } from "./speechProtocol";

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
  speechEvent: [event: SpeechEvent];
}>();

const hosts = new Map<string, InstanceType<typeof ComponentHost>>();
function speechCommand(command: SpeechCommand) {
  const host = hosts.get(command.component_id);
  if (!host) throw Object.assign(new Error("Digital human is not configured."), { code: "DIGITAL_HUMAN_NOT_CONFIGURED" });
  return host.speechCommand(command);
}

const container = ref<HTMLElement | null>(null);
const runtimeViewport = ref(
  resolveRuntimeViewport({
    canvasWidth: props.document.canvas.width,
    canvasHeight: props.document.canvas.height,
    containerWidth: 0,
    containerHeight: 0,
  }),
);
const parameterVersion = ref(0);
const dataRuntime = createDataRuntime(props.queryComponent);
const dataStates = computed(() => Object.fromEntries(
  components.value.map((component) => [component.id, dataRuntime.state(component.id)]),
));
const parameterSource = ref<"runtime" | "host">("runtime");
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
const themeTokens = computed(() => resolveThemeTokens(props.document.theme));
const themeStyle = computed(() =>
  resolveTheme({ tokens: themeTokens.value }),
);
const canvasStyle = computed(() => {
  const background = props.document.canvas.background;
  const color =
    background && typeof background.color === "string"
      ? background.color
      : typeof themeTokens.value.canvas_background === "string"
        ? themeTokens.value.canvas_background
        : "#071522";
  return {
    ...themeStyle.value,
    width: `${props.document.canvas.width}px`,
    height: `${props.document.canvas.height}px`,
    backgroundColor: color,
    transform: `scale(${runtimeViewport.value.scale})`,
  };
});
const viewportStyle = computed(() => ({
  width: `${runtimeViewport.value.viewportWidth}px`,
  height: `${runtimeViewport.value.viewportHeight}px`,
}));

function hasBinding(binding: unknown): binding is Record<string, JsonValue> {
  return (
    binding !== null &&
    typeof binding === "object" &&
    !Array.isArray(binding) &&
    Object.keys(binding).length > 0
  );
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

function stopSpeech(): void {
  for (const component of components.value) {
    if (component.type === "builtin.digital_human") {
      try {
        hosts.get(component.id)?.speechCommand({ component_id: component.id, action: "stop" });
      } catch (error) {
        emit("error", error);
      }
    }
  }
}

async function refresh(): Promise<void> {
  stopSpeech();
  dataRuntime.beginGeneration();
  const parameters = parameterState.values();
  const loads = components.value
    .filter((component) => hasBinding(component.data_binding) && component.data_binding?.source !== "components")
    .map((component) =>
      dataRuntime
        .load(component.id, component.data_binding!, parameters, component.type)
        .catch((error: unknown) => {
          if (!isAbortError(error)) {
            emit("error", error);
          }
        }),
    );
  await Promise.all(loads);
}

function setParameter(
  name: string,
  value: JsonValue,
  source: ParameterMutationSource = "runtime",
): void {
  setParameters({ [name]: value }, source);
}

function setParameters(
  values: RuntimeParameters,
  source: ParameterMutationSource = "runtime",
): void {
  const nextState = createParameterState(
    props.document.parameters ?? [],
    parameterState.values(),
  );
  for (const [name, value] of Object.entries(values)) {
    nextState.set(name, value, source);
  }
  parameterState = nextState;
  parameterSource.value = source === "host" ? "host" : "runtime";
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
  runtimeViewport.value = resolveRuntimeViewport({
    canvasWidth: props.document.canvas.width,
    canvasHeight: props.document.canvas.height,
    containerWidth: host.clientWidth,
    containerHeight: host.clientHeight,
  });
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
  speechCommand,
  stopSpeech,
  getParameters: () => parameterState.values(),
  refresh,
  setParameter,
  setParameters,
});
</script>

<template>
  <div
    ref="container"
    class="screen-runtime"
    :data-mode="mode"
    :data-density="runtimeViewport.density"
    :data-overflow="runtimeViewport.overflow ? 'scroll' : 'fit'"
    :data-parameter-version="parameterVersion"
  >
    <div class="screen-runtime__viewport" :style="viewportStyle">
      <div class="screen-runtime__canvas" :style="canvasStyle">
        <ComponentHost
          v-for="component in components"
          :key="component.id"
          :ref="(host) => { if (host) hosts.set(component.id, host as InstanceType<typeof ComponentHost>); else hosts.delete(component.id); }"
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
          :data-states="dataStates"
          :parameters="parameterState.values()"
          :parameter-source="parameterSource"
          :theme="themeTokens"
          :mode="mode"
          @interaction="handleInteraction"
          @speech-event="emit('speechEvent', $event)"
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

.screen-runtime[data-overflow="scroll"] {
  overflow: auto;
  overscroll-behavior: contain;
  place-items: start;
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
