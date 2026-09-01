<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  ref,
  watch,
} from "vue";
import { RouterLink, useRoute } from "vue-router";

import type { DashboardDocument } from "../../contracts";
import { ApiError } from "../../lib/api";
import InlineNotice from "../../ui/InlineNotice.vue";
import type { JsonValue } from "../query/types";
import ScreenRuntime from "../runtime/ScreenRuntime.vue";
import {
  exchangeStandaloneKey,
  getEmbedDocument,
  getPreviewDocument,
  getStandaloneDocument,
  loadEmbedAsset,
  loadPreviewAsset,
  loadStandaloneAsset,
  queryEmbedComponent,
  queryPreviewComponent,
  queryStandaloneComponent,
} from "./api";
import {
  createEmbedBridge,
  type EmbedBridge,
} from "./embedBridge";
import type {
  EmbedPlayerDocument,
  PlayerDocument,
  PlayerMode,
} from "./types";

const props = defineProps<{
  mode: PlayerMode;
  screenId?: string;
}>();

const route = useRoute();
const resolvedScreenId = computed(
  () => props.screenId ?? String(route.params.id ?? ""),
);
const document = ref<DashboardDocument | null>(null);
const screenName = ref("");
const initialParameters = ref<Record<string, JsonValue>>({});
const mutableParameters = ref<Set<string>>(new Set());
const loading = ref(true);
const loadError = ref<ApiError | null>(null);
interface RuntimeController {
  getParameters(): Record<string, JsonValue>;
  refresh(): Promise<void>;
  setParameter(
    name: string,
    value: JsonValue,
    source?: "runtime" | "host",
  ): void;
  setParameters(
    values: Record<string, JsonValue>,
    source?: "runtime" | "host",
  ): void;
}
const runtime = ref<RuntimeController | null>(null);
let controller: AbortController | null = null;
let embedBridge: EmbedBridge | null = null;
const bootstrapKey = ref(
  props.mode === "standalone" && typeof route.query.key === "string"
    ? route.query.key
    : "",
);
const embedTicket = ref(
  props.mode === "embed" && typeof route.query.ticket === "string"
    ? route.query.ticket
    : "",
);

function createEmbedInstanceId(): string {
  return (
    globalThis.crypto?.randomUUID?.() ??
    `datapulse-embed-${Date.now()}-${Math.random().toString(36).slice(2)}`
  );
}

const embedInstanceId =
  props.mode === "embed"
    ? (typeof route.query.instance_id === "string" &&
      route.query.instance_id.trim()) ||
      createEmbedInstanceId()
    : "";
if (
  (props.mode === "standalone" && route.query.key !== undefined) ||
  (props.mode === "embed" &&
    (route.query.ticket !== undefined ||
      route.query.instance_id !== undefined))
) {
  window.history.replaceState(window.history.state, "", route.path);
}

function playerError(code: string, message: string): Error & { code: string } {
  return Object.assign(new Error(message), { code });
}

async function configureEmbedBridge(allowedOrigin: string): Promise<void> {
  embedBridge?.destroy();
  await nextTick();
  embedBridge = createEmbedBridge({
    allowedOrigin,
    instanceId: embedInstanceId,
    refresh: async () => {
      if (!runtime.value) {
        throw playerError("EMBED_PLAYER_NOT_READY", "大屏尚未就绪。");
      }
      await runtime.value.refresh();
    },
    setParameters: (values) => {
      if (!runtime.value) {
        throw playerError("EMBED_PLAYER_NOT_READY", "大屏尚未就绪。");
      }
      const names = Object.keys(values);
      if (!names.every((name) => mutableParameters.value.has(name))) {
        throw playerError(
          "EMBED_PARAMETER_DENIED",
          "宿主系统不能修改该大屏参数。",
        );
      }
      try {
        runtime.value.setParameters(values, "host");
      } catch {
        throw playerError(
          "EMBED_PARAMETER_INVALID",
          "宿主系统提供的大屏参数无效。",
        );
      }
    },
    getParameters: () => {
      if (!runtime.value) {
        throw playerError("EMBED_PLAYER_NOT_READY", "大屏尚未就绪。");
      }
      return runtime.value.getParameters();
    },
    fullscreen: async (enabled) => {
      if (enabled) {
        if (!window.document.documentElement.requestFullscreen) {
          throw playerError(
            "EMBED_FULLSCREEN_UNAVAILABLE",
            "当前浏览器不支持全屏。",
          );
        }
        await window.document.documentElement.requestFullscreen();
      } else if (window.document.fullscreenElement) {
        await window.document.exitFullscreen();
      }
    },
  });
  embedBridge.ready();
}

async function load(): Promise<void> {
  controller?.abort();
  embedBridge?.destroy();
  embedBridge = null;
  const nextController = new AbortController();
  controller = nextController;
  loading.value = true;
  loadError.value = null;
  try {
    let loaded: PlayerDocument | EmbedPlayerDocument;
    if (props.mode === "preview") {
      loaded = await getPreviewDocument(
        resolvedScreenId.value,
        nextController.signal,
      );
    } else if (props.mode === "standalone") {
      const key = bootstrapKey.value;
      bootstrapKey.value = "";
      if (key) {
        await exchangeStandaloneKey(
          resolvedScreenId.value,
          key,
          nextController.signal,
        );
      }
      loaded = await getStandaloneDocument(
        resolvedScreenId.value,
        nextController.signal,
      );
    } else if (props.mode === "embed") {
      if (!embedTicket.value) {
        throw new ApiError({
          code: "EMBED_TICKET_REQUIRED",
          message: "嵌入票据缺失。",
          requestId: "",
          status: 401,
        });
      }
      loaded = await getEmbedDocument(
        resolvedScreenId.value,
        embedTicket.value,
        nextController.signal,
      );
    } else {
      throw new Error("This playback mode is not configured yet.");
    }
    if (!nextController.signal.aborted && controller === nextController) {
      document.value = loaded.document;
      screenName.value = loaded.name;
      if (props.mode === "embed" && "allowed_origin" in loaded) {
        const embedded = loaded as EmbedPlayerDocument;
        initialParameters.value = embedded.parameters;
        mutableParameters.value = new Set(embedded.mutable_parameters);
        await configureEmbedBridge(embedded.allowed_origin);
      }
    }
  } catch (reason) {
    if (!nextController.signal.aborted && controller === nextController) {
      loadError.value =
        reason instanceof ApiError
          ? reason
          : new ApiError({
              code: "PLAYER_LOAD_FAILED",
              message: "暂时无法加载大屏。",
              requestId: "",
              status: 500,
            });
    }
  } finally {
    if (controller === nextController) {
      loading.value = false;
    }
  }
}

watch([resolvedScreenId, () => props.mode], () => void load(), {
  immediate: true,
});

onBeforeUnmount(() => {
  controller?.abort();
  embedBridge?.destroy();
});

const queryComponent = async (
  componentId: string,
  parameters: Parameters<typeof queryPreviewComponent>[2],
  signal?: AbortSignal,
) => {
  if (props.mode === "standalone") {
    return queryStandaloneComponent(
      resolvedScreenId.value,
      componentId,
      parameters,
      signal,
    );
  }
  if (props.mode === "embed") {
    const overrides = Object.fromEntries(
      Object.entries(parameters).filter(([name]) =>
        mutableParameters.value.has(name),
      ),
    );
    return queryEmbedComponent(
      resolvedScreenId.value,
      componentId,
      overrides,
      embedTicket.value,
      signal,
    );
  }
  return queryPreviewComponent(
    resolvedScreenId.value,
    componentId,
    parameters,
    signal,
  );
};

async function loadAsset(
  assetId: string,
  signal?: AbortSignal,
): Promise<string> {
  try {
    if (props.mode === "standalone") {
      return await loadStandaloneAsset(
        resolvedScreenId.value,
        assetId,
        signal,
      );
    }
    if (props.mode === "embed") {
      return await loadEmbedAsset(
        resolvedScreenId.value,
        assetId,
        embedTicket.value,
        signal,
      );
    }
    return await loadPreviewAsset(assetId, signal);
  } catch (error) {
    if (props.mode === "embed") {
      embedBridge?.reportError(error);
    }
    throw error;
  }
}

function handleRuntimeError(error: unknown): void {
  if (props.mode === "embed") {
    embedBridge?.reportError(error);
  }
}
</script>

<template>
  <main class="player-page" :data-player-mode="mode">
    <header v-if="mode === 'preview'" class="player-preview-bar">
      <div>
        <strong>草稿预览</strong>
        <span>{{ screenName }}</span>
      </div>
      <RouterLink
        class="secondary-button"
        :to="{ name: 'screen-edit', params: { id: resolvedScreenId } }"
      >
        返回编辑
      </RouterLink>
    </header>
    <section class="player-stage" aria-label="大屏播放区域">
      <p v-if="loading" class="player-status" role="status">正在加载大屏…</p>
      <div
        v-else-if="loadError && mode !== 'preview'"
        class="player-neutral-error"
        role="alert"
      >
        <strong>无法播放此大屏</strong>
        <p>访问已失效，或大屏暂不可用。</p>
      </div>
      <InlineNotice v-else-if="loadError" tone="error">
        <p>{{ loadError.message }}</p>
        <code v-if="loadError.requestId">{{ loadError.requestId }}</code>
      </InlineNotice>
      <ScreenRuntime
        v-else-if="document"
        ref="runtime"
        :document="document"
        :initial-parameters="initialParameters"
        :load-asset="loadAsset"
        :mode="mode"
        :query-component="queryComponent"
        @error="handleRuntimeError"
      />
    </section>
  </main>
</template>
