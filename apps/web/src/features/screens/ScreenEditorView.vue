<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";

import { ApiError } from "../../lib/api";
import InlineNotice from "../../ui/InlineNotice.vue";
import AiAnalysisPanel from "../ai/AiAnalysisPanel.vue";
import type { JsonValue } from "../query/types";
import { defaultComponentRegistry } from "../runtime/registry";
import { publishScreen } from "./api";
import { componentTypeToChartType } from "./editor/chartSuggestion";
import ComponentLibrary from "./editor/ComponentLibrary.vue";
import EditorToolbar from "./editor/EditorToolbar.vue";
import InspectorPanel from "./editor/InspectorPanel.vue";
import LayersPanel from "./editor/LayersPanel.vue";
import ScreenCanvas from "./editor/ScreenCanvas.vue";
import { useScreenEditorStore } from "./editor/store";

const route = useRoute();
const store = useScreenEditorStore();
const screenId = computed(() => String(route.params.id));
const canvas = ref<InstanceType<typeof ScreenCanvas> | null>(null);
const publishConfirmationOpen = ref(false);
const publishing = ref(false);
const publishError = ref<ApiError | null>(null);
const publishMessage = ref("");
const selectedComponent = computed(() => {
  if (store.selection.length !== 1) {
    return null;
  }
  return store.document?.components?.find(
    (component) => component.id === store.selection[0],
  ) ?? null;
});
const selectedDefinition = computed(() =>
  selectedComponent.value
    ? defaultComponentRegistry.get(selectedComponent.value.type)
    : undefined,
);
const selectedAiTarget = computed(() =>
  selectedComponent.value
    ? componentTypeToChartType(selectedComponent.value.type)
    : null,
);

function datasetIdFromSelection(): string {
  const chartSpec = selectedComponent.value?.data_binding?.chart_spec;
  if (
    chartSpec &&
    typeof chartSpec === "object" &&
    !Array.isArray(chartSpec) &&
    typeof chartSpec.dataset_id === "string"
  ) {
    return chartSpec.dataset_id;
  }
  return "";
}

const selectedDatasetId = computed(() => {
  return datasetIdFromSelection();
});
const selectedCurrentProps = computed(
  () => (selectedComponent.value?.props ?? {}) as Record<string, JsonValue>,
);
const canUseAiPanel = computed(
  () =>
    selectedComponent.value !== null &&
    selectedDefinition.value?.dataCapability !== "none" &&
    selectedAiTarget.value !== null,
);

const saveLabel = computed(() => {
  const labels = {
    idle: "尚未加载",
    dirty: "未保存",
    saving: "保存中…",
    saved: "已保存",
    failed: "保存失败",
    conflict: "草稿冲突",
  };
  return labels[store.saveState];
});

onMounted(() => store.load(screenId.value));

async function requestPublish(): Promise<void> {
  publishError.value = null;
  publishMessage.value = "";
  await store.saveNow();
  if (store.saveState === "saved") {
    publishConfirmationOpen.value = true;
  }
}

async function confirmPublish(): Promise<void> {
  if (!store.screen || publishing.value) {
    return;
  }
  publishing.value = true;
  publishError.value = null;
  try {
    const published = await publishScreen(
      store.screen.id,
      store.screen.draft_revision,
    );
    store.screen = published as never;
    publishConfirmationOpen.value = false;
    publishMessage.value = "发布成功";
  } catch (reason) {
    publishError.value =
      reason instanceof ApiError
        ? reason
        : new ApiError({
            code: "SCREEN_PUBLISH_FAILED",
            message: "暂时无法发布大屏。",
            requestId: "",
            status: 500,
          });
  } finally {
    publishing.value = false;
  }
}
</script>

<template>
  <section class="screen-editor-page" aria-label="大屏编辑器">
    <p v-if="store.loading" class="loading-copy" role="status">
      正在加载大屏编辑器…
    </p>
    <InlineNotice v-else-if="store.loadError" tone="error">
      <p>{{ store.loadError.message }}</p>
      <code v-if="store.loadError.requestId">
        {{ store.loadError.requestId }}
      </code>
    </InlineNotice>

    <template v-else-if="store.screen && store.document">
      <EditorToolbar
        :save-label="saveLabel"
        :publishing="publishing"
        :zoom="canvas?.zoom ?? 0.5"
        @align="canvas?.alignSelection($event)"
        @publish="requestPublish"
        @zoom="canvas?.setZoom($event)"
      />

      <InlineNotice v-if="publishMessage" class="editor-conflict" tone="info">
        <p>{{ publishMessage }}</p>
      </InlineNotice>
      <InlineNotice v-if="publishError" class="editor-conflict" tone="error">
        <p>{{ publishError.message }}</p>
        <code v-if="publishError.requestId">{{ publishError.requestId }}</code>
      </InlineNotice>
      <InlineNotice
        v-if="store.saveState === 'conflict'"
        class="editor-conflict"
        tone="error"
      >
        <p>草稿已在其他页面发生变化，请重新载入后继续编辑。</p>
      </InlineNotice>

      <div class="editor-workspace">
        <aside class="editor-panel editor-panel--left" aria-label="组件与图层">
          <ComponentLibrary />
          <LayersPanel />
        </aside>
        <main class="editor-canvas-region" aria-label="大屏画布">
          <ScreenCanvas ref="canvas" />
        </main>
        <aside class="editor-panel editor-panel--right" aria-label="属性面板">
          <InspectorPanel />
          <AiAnalysisPanel
            v-if="canUseAiPanel && selectedComponent"
            :key="selectedComponent.id"
            :initial-dataset-id="selectedDatasetId"
            :target-component-type="selectedAiTarget ?? undefined"
            :current-props="selectedCurrentProps"
            :can-apply="true"
            apply-label="应用到当前组件"
            @apply-chart="
              store.applyChartSuggestion(selectedComponent.id, $event)
            "
          />
          <section v-else class="editor-panel__hint" aria-label="AI 使用说明">
            <h2>AI 分析</h2>
            <p>选中一个可绑定数据的组件后，就可以生成图表建议并直接应用。</p>
          </section>
        </aside>
      </div>

      <div
        v-if="publishConfirmationOpen"
        class="dialog-backdrop"
        role="presentation"
        @click.self="publishConfirmationOpen = false"
      >
        <section
          class="dialog-card publish-confirmation"
          role="dialog"
          aria-modal="true"
          aria-labelledby="publish-confirmation-title"
        >
          <div class="dialog-heading">
            <div>
              <h2 id="publish-confirmation-title">确认发布大屏</h2>
              <p>发布将覆盖当前线上大屏，且无法直接回滚。</p>
            </div>
          </div>
          <p>如需备份，请先复制大屏。</p>
          <div class="dialog-actions">
            <button
              class="secondary-button"
              type="button"
              :disabled="publishing"
              @click="publishConfirmationOpen = false"
            >
              取消
            </button>
            <button
              class="primary-button"
              data-action="confirm-publish"
              type="button"
              :disabled="publishing"
              @click="confirmPublish"
            >
              {{ publishing ? "发布中…" : "确认发布" }}
            </button>
          </div>
        </section>
      </div>
    </template>
  </section>
</template>

<style scoped>
.editor-panel__hint {
  display: grid;
  gap: 8px;
  padding: 16px;
  border: 1px dashed rgb(148 163 184 / 25%);
  border-radius: 14px;
}

.editor-panel__hint h2,
.editor-panel__hint p {
  margin: 0;
}
</style>
