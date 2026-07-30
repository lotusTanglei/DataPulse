<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import type { DashboardDocument } from "../../contracts";
import { ApiError } from "../../lib/api";
import InlineNotice from "../../ui/InlineNotice.vue";
import ScreenRuntime from "../runtime/ScreenRuntime.vue";
import {
  exchangeStandaloneKey,
  getPreviewDocument,
  getStandaloneDocument,
  loadPreviewAsset,
  loadStandaloneAsset,
  queryPreviewComponent,
  queryStandaloneComponent,
} from "./api";
import type { PlayerMode } from "./types";

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
const loading = ref(true);
const loadError = ref<ApiError | null>(null);
let controller: AbortController | null = null;
const bootstrapKey = ref(
  props.mode === "standalone" && typeof route.query.key === "string"
    ? route.query.key
    : "",
);
if (props.mode === "standalone" && route.query.key !== undefined) {
  window.history.replaceState(window.history.state, "", route.path);
}

async function load(): Promise<void> {
  controller?.abort();
  const nextController = new AbortController();
  controller = nextController;
  loading.value = true;
  loadError.value = null;
  try {
    let loaded;
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
    } else {
      throw new Error("This playback mode is not configured yet.");
    }
    if (!nextController.signal.aborted && controller === nextController) {
      document.value = loaded.document;
      screenName.value = loaded.name;
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

onBeforeUnmount(() => controller?.abort());

const queryComponent = (
  componentId: string,
  parameters: Parameters<typeof queryPreviewComponent>[2],
  signal?: AbortSignal,
) =>
  props.mode === "standalone"
    ? queryStandaloneComponent(
        resolvedScreenId.value,
        componentId,
        parameters,
        signal,
      )
    : queryPreviewComponent(
        resolvedScreenId.value,
        componentId,
        parameters,
        signal,
      );

const loadAsset = (assetId: string, signal?: AbortSignal) =>
  props.mode === "standalone"
    ? loadStandaloneAsset(resolvedScreenId.value, assetId, signal)
    : loadPreviewAsset(assetId, signal);
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
        :document="document"
        :load-asset="loadAsset"
        :mode="mode"
        :query-component="queryComponent"
      />
    </section>
  </main>
</template>
