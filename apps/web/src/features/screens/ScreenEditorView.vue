<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";

import { ApiError } from "../../lib/api";
import InlineNotice from "../../ui/InlineNotice.vue";
import AiAnalysisPanel from "../ai/AiAnalysisPanel.vue";
import AiEditPanel from "../ai/AiEditPanel.vue";
import type { JsonValue } from "../query/types";
import { defaultComponentRegistry } from "../runtime/registry";
import { generateDisplayKey, publishScreen, updateScreenAccessPolicy } from "./api";
import { componentTypeToChartType } from "./editor/chartSuggestion";
import ComponentLibrary from "./editor/ComponentLibrary.vue";
import EditorToolbar from "./editor/EditorToolbar.vue";
import InspectorPanel from "./editor/InspectorPanel.vue";
import LayersPanel from "./editor/LayersPanel.vue";
import ScreenCanvas from "./editor/ScreenCanvas.vue";
import ScreenAccessPolicyPanel from "./ScreenAccessPolicyPanel.vue";
import type { ScreenAccessPolicy } from "./types";
import { useScreenEditorStore } from "./editor/store";

const route = useRoute();
const store = useScreenEditorStore();
const screenId = computed(() => String(route.params.id));
const canvas = ref<InstanceType<typeof ScreenCanvas> | null>(null);
const publishConfirmationOpen = ref(false);
const publishing = ref(false);
const publishError = ref<ApiError | null>(null);
const publishMessage = ref("");
const usagePanelOpen = ref(false);
const deliveryPanelVisible = computed(
  () => usagePanelOpen.value || Boolean(store.screen?.published_at),
);
const usageLoading = ref(false);
const usageError = ref("");
const accessPolicySaving = ref(false);
const accessPolicyError = ref<ApiError | null>(null);
const displayKey = ref("");
const standaloneUrl = computed(() =>
  displayKey.value
    ? `${window.location.origin}/play/${encodeURIComponent(screenId.value)}?key=${encodeURIComponent(displayKey.value)}`
    : "",
);
const embedUrl = computed(
  () => `${window.location.origin}/embed/${encodeURIComponent(screenId.value)}?ticket=<短期 ticket>`,
);
const embedSnippet = computed(
  () => `<iframe src="${embedUrl.value}" width="100%" height="600"></iframe>`,
);
const selectedComponent = computed(() => {
  if (store.selection.length !== 1) {
    return null;
  }
  return store.document?.components?.find(
    (component) => component.id === store.selection[0],
  ) ?? null;
});
const canUngroupSelection = computed(() =>
  store.selection.some((id) => {
    const component = store.document?.components?.find((item) => item.id === id);
    return Boolean(component?.state?.group_id);
  }),
);
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
const documentDatasetIds = computed(() => {
  const ids = new Set<string>();
  for (const component of store.document?.components ?? []) {
    const chartSpec = component.data_binding?.chart_spec;
    if (
      chartSpec &&
      typeof chartSpec === "object" &&
      !Array.isArray(chartSpec) &&
      typeof chartSpec.dataset_id === "string"
    ) {
      ids.add(chartSpec.dataset_id);
    }
  }
  return [...ids];
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
    publishMessage.value = "发布完成";
    usagePanelOpen.value = true;
    displayKey.value = "";
    usageError.value = "";
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

async function createStandaloneLink(): Promise<void> {
  usageLoading.value = true;
  usageError.value = "";
  try {
    displayKey.value = (await generateDisplayKey(screenId.value)).key;
  } catch (reason) {
    usageError.value = reason instanceof ApiError ? reason.message : "暂时无法生成播放链接。";
  } finally {
    usageLoading.value = false;
  }
}

async function copyText(value: string): Promise<void> {
  if (!value) return;
  await navigator.clipboard?.writeText(value);
}

async function saveAccessPolicy(policy: ScreenAccessPolicy): Promise<void> {
  if (!store.screen || accessPolicySaving.value) {
    return;
  }
  accessPolicySaving.value = true;
  accessPolicyError.value = null;
  try {
    store.screen = await updateScreenAccessPolicy(store.screen.id, policy);
  } catch (reason) {
    accessPolicyError.value =
      reason instanceof ApiError
        ? reason
        : new ApiError({
            code: "SCREEN_ACCESS_POLICY_FAILED",
            message: "暂时无法保存访问限制。",
            requestId: "",
            status: 500,
          });
  } finally {
    accessPolicySaving.value = false;
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
        :show-grid="canvas?.showGrid ?? true"
        :snap-enabled="canvas?.snapEnabled ?? true"
        :selection-count="store.selection.length"
        :can-ungroup="canUngroupSelection"
        @align="canvas?.alignSelection($event)"
        @distribute="canvas?.distributeSelection($event)"
        @group="canvas?.groupSelection()"
        @publish="requestPublish"
        @refresh="canvas?.refreshData()"
        @toggle-grid="canvas?.toggleGrid()"
        @toggle-snap="canvas?.toggleSnap()"
        @ungroup="canvas?.ungroupSelection()"
        @zoom="canvas?.setZoom($event)"
      />

      <InlineNotice v-if="publishMessage" class="editor-conflict" tone="info">
        <p>{{ publishMessage }}</p>
      </InlineNotice>
      <section
        v-if="deliveryPanelVisible"
        class="publish-usage-panel"
        aria-labelledby="publish-usage-title"
      >
        <div>
          <h2 id="publish-usage-title">发布成功，接下来这样使用</h2>
          <p>独立播放适合直接打开；嵌入第三方系统时请由宿主后端申请短期 ticket。</p>
        </div>
        <div class="publish-usage-block">
          <h3>独立播放</h3>
          <button
            class="secondary-button"
            data-action="generate-play-link"
            type="button"
            :disabled="usageLoading"
            @click="createStandaloneLink"
          >
            {{ usageLoading ? "生成中…" : "生成播放链接" }}
          </button>
          <div v-if="standaloneUrl" class="publish-usage-link">
            <code>{{ standaloneUrl }}</code>
            <button class="table-action" type="button" @click="copyText(standaloneUrl)">
              复制
            </button>
            <a :href="standaloneUrl" target="_blank" rel="noreferrer">打开</a>
          </div>
        </div>
        <div class="publish-usage-block">
          <h3>嵌入第三方系统</h3>
          <p>宿主后端使用 embed API key 调用 <code>POST /api/embed/tickets</code>，再把短期 ticket 传给页面。</p>
          <code class="publish-usage-code">&lt;iframe src="{{ embedUrl }}" width="100%" height="600" /&gt;</code>
          <button class="table-action" type="button" @click="copyText(embedSnippet)">
            复制嵌入示例
          </button>
        </div>
        <p v-if="usageError" class="publish-usage-error">{{ usageError }}</p>
      </section>
      <ScreenAccessPolicyPanel
        v-if="deliveryPanelVisible && store.screen"
        :policy="store.screen.access_policy"
        :saving="accessPolicySaving"
        :error="accessPolicyError"
        @save="saveAccessPolicy"
      />
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
          <AiEditPanel
            v-if="store.selection.length > 0 && store.document"
            :key="`edit-${store.selection.join('-')}`"
            :document="store.document"
            :selected-component-ids="store.selection"
            :dataset-ids="documentDatasetIds"
            @apply="store.applyAiEdit"
          />
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

.publish-usage-panel {
  display: grid;
  gap: 14px;
  margin: 12px 0;
  padding: 16px;
  border: 1px solid rgb(99 102 241 / 28%);
  border-radius: 14px;
  background: rgb(99 102 241 / 8%);
}

.publish-usage-panel h2,
.publish-usage-panel h3,
.publish-usage-panel p {
  margin: 0;
}

.publish-usage-block {
  display: grid;
  gap: 8px;
}

.publish-usage-link {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.publish-usage-link code,
.publish-usage-code {
  overflow-wrap: anywhere;
  padding: 8px;
  border-radius: 8px;
  background: rgb(15 23 42 / 65%);
}

.publish-usage-error {
  color: #fca5a5;
}
</style>
