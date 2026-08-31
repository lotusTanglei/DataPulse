<script setup lang="ts">
import { X } from "@lucide/vue";
import { computed, ref, watch } from "vue";

import { ApiError } from "../../lib/api";
import InlineNotice from "../../ui/InlineNotice.vue";
import { listDatasets } from "../datasets/api";
import type { Dataset } from "../datasets/types";
import { generateScreen, getAiStatus } from "./api";
import ScreenDraftPreview from "./ScreenDraftPreview.vue";
import type { AiHealth, AiScreenResponse } from "./types";

const props = withDefaults(
  defineProps<{
    open: boolean;
    submitting?: boolean;
  }>(),
  {
    submitting: false,
  },
);

const emit = defineEmits(["close", "confirm"]);

const datasets = ref<Dataset[]>([]);
const loadingDatasets = ref(false);
const datasetError = ref<ApiError | null>(null);
const generateError = ref<ApiError | null>(null);
const formError = ref("");
const generating = ref(false);
const screenName = ref("");
const question = ref("");
const selectedDatasetIds = ref<string[]>([]);
const result = ref<AiScreenResponse | null>(null);
const aiStatus = ref<AiHealth | null>(null);

const canClose = computed(() => !generating.value && !props.submitting);

async function loadDatasets(): Promise<void> {
  if (datasets.value.length > 0) {
    return;
  }
  loadingDatasets.value = true;
  datasetError.value = null;
  try {
    datasets.value = await listDatasets();
  } catch (reason) {
    datasetError.value =
      reason instanceof ApiError
        ? reason
        : new ApiError({
            code: "AI_DATASETS_FAILED",
            message: "暂时无法加载数据集列表。",
            requestId: "",
            status: 500,
          });
  } finally {
    loadingDatasets.value = false;
  }
}

async function loadAiStatus(): Promise<void> {
  try {
    aiStatus.value = await getAiStatus();
  } catch {
    aiStatus.value = null;
  }
}

function reset(): void {
  screenName.value = "";
  question.value = "";
  selectedDatasetIds.value = [];
  formError.value = "";
  generateError.value = null;
  result.value = null;
}

async function submit(): Promise<void> {
  const name = screenName.value.trim();
  const prompt = question.value.trim();
  if (!name || !prompt || selectedDatasetIds.value.length === 0) {
    formError.value = "请输入名称、描述目标，并至少选择一个数据集。";
    return;
  }
  generating.value = true;
  formError.value = "";
  generateError.value = null;
  try {
    result.value = await generateScreen({
      question: prompt,
      dataset_ids: selectedDatasetIds.value,
      theme: "dark",
    });
  } catch (reason) {
    generateError.value =
      reason instanceof ApiError
        ? reason
        : new ApiError({
            code: "AI_SCREEN_FAILED",
            message: "暂时无法生成大屏草稿。",
            requestId: "",
            status: 500,
          });
  } finally {
    generating.value = false;
  }
}

function confirm(): void {
  if (!result.value || props.submitting) {
    return;
  }
  emit("confirm", {
    name: screenName.value.trim(),
    result: result.value as AiScreenResponse,
  });
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      reset();
      void loadDatasets();
      void loadAiStatus();
    }
  },
  { immediate: true },
);
</script>

<template>
  <div
    v-if="open"
    class="dialog-backdrop"
    role="presentation"
    @mousedown.self="canClose ? emit('close') : undefined"
  >
    <section
      class="dialog-card ai-screen-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="ai-screen-title"
    >
      <div class="dialog-heading">
        <div>
          <h2 id="ai-screen-title">AI 生成大屏</h2>
          <p>先生成草稿，确认后再创建到工作区。</p>
        </div>
        <button
          class="dialog-close"
          type="button"
          aria-label="关闭"
          :disabled="!canClose"
          @click="emit('close')"
        >
          <X :size="16" aria-hidden="true" />
        </button>
      </div>

      <InlineNotice v-if="datasetError" tone="error">
        <p>{{ datasetError.message }}</p>
        <code v-if="datasetError.requestId">{{ datasetError.requestId }}</code>
      </InlineNotice>
      <InlineNotice v-if="generateError" tone="error">
        <p>{{ generateError.message }}</p>
        <code v-if="generateError.requestId">{{ generateError.requestId }}</code>
      </InlineNotice>
      <InlineNotice v-if="aiStatus?.status === 'unconfigured'" tone="info">
        <p>AI 服务尚未配置，无法生成草稿。请先配置 AI 服务后再试。</p>
      </InlineNotice>

      <form class="dialog-form ai-screen-dialog__form" @submit.prevent="submit">
        <label class="form-field" :data-invalid="formError ? 'true' : 'false'">
          <span class="form-field__heading">大屏名称</span>
          <input
            v-model="screenName"
            name="aiScreenName"
            autocomplete="off"
            placeholder="例如：区域经营驾驶舱"
            :disabled="generating || submitting"
            @input="formError = ''; result = null"
          />
        </label>

        <label class="form-field">
          <span class="form-field__heading">需求描述</span>
          <textarea
            v-model="question"
            name="aiScreenQuestion"
            rows="4"
            placeholder="例如：做一个区域经营总览，突出销售额、订单数、趋势和区域对比。"
            :disabled="generating || submitting"
            @input="formError = ''; result = null"
          />
        </label>

        <fieldset class="ai-screen-dialog__datasets">
          <legend>数据集</legend>
          <p v-if="loadingDatasets" class="ai-screen-dialog__hint">正在加载数据集…</p>
          <p
            v-else-if="datasets.length === 0"
            class="ai-screen-dialog__hint"
          >
            暂无可用数据集。
          </p>
          <template v-else>
            <label
              v-for="dataset in datasets"
              :key="dataset.id"
              class="ai-screen-dialog__dataset-option"
            >
              <input
                v-model="selectedDatasetIds"
                type="checkbox"
                name="aiScreenDatasets"
                :value="dataset.id"
                :disabled="generating || submitting"
                @change="formError = ''; result = null"
              />
              <span>
                <strong>{{ dataset.name }}</strong>
                <code>{{ dataset.id }}</code>
              </span>
            </label>
          </template>
        </fieldset>

        <span v-if="formError" class="form-field__error">{{ formError }}</span>

        <div class="dialog-actions">
          <button
            class="secondary-button"
            type="button"
            :disabled="generating || submitting"
            @click="emit('close')"
          >
            取消
          </button>
          <button
            class="primary-button"
            type="submit"
            :disabled="generating || submitting"
          >
            {{ generating ? "正在生成…" : "生成草稿" }}
          </button>
        </div>
      </form>

      <section
        v-if="result"
        class="ai-screen-dialog__result"
        aria-label="AI 大屏草稿结果"
      >
        <h3>生成结果</h3>
        <p>{{ result.explanation }}</p>
        <div class="ai-screen-dialog__meta">
          <span>
            画布
            {{ result.document.canvas.width }} × {{ result.document.canvas.height }}
          </span>
          <span>
            组件 {{ result.document.components?.length ?? 0 }}
          </span>
        </div>
        <ScreenDraftPreview :document="result.document" />
        <ul
          v-if="result.warnings.length > 0"
          class="ai-screen-dialog__warnings"
          aria-label="AI 警告"
        >
          <li v-for="warning in result.warnings" :key="warning">
            {{ warning }}
          </li>
        </ul>
        <div class="dialog-actions">
          <button
            class="primary-button"
            type="button"
            data-action="confirm-ai-screen"
            :disabled="submitting"
            @click="confirm"
          >
            {{ submitting ? "正在创建…" : "创建草稿并进入编辑器" }}
          </button>
        </div>
      </section>
    </section>
  </div>
</template>

<style scoped>
.ai-screen-dialog {
  display: grid;
  gap: 16px;
  width: min(760px, calc(100vw - 32px));
  max-height: calc(100vh - 32px);
  overflow-y: auto;
  color: var(--dp-text);
}

.ai-screen-dialog .dialog-heading p {
  color: #5f5e5b;
}

.ai-screen-dialog__form,
.ai-screen-dialog__result {
  display: grid;
  gap: 14px;
}

.ai-screen-dialog__datasets {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--dp-border);
  border-radius: 12px;
  background: #fbfbfa;
}

.ai-screen-dialog__datasets legend {
  padding: 0 6px;
  color: var(--dp-text);
  font-size: 13px;
}

.ai-screen-dialog__dataset-option {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.ai-screen-dialog__dataset-option span {
  display: grid;
  gap: 4px;
}

.ai-screen-dialog__hint,
.ai-screen-dialog__result h3,
.ai-screen-dialog__result p,
.ai-screen-dialog__warnings {
  margin: 0;
}

.ai-screen-dialog__hint,
.ai-screen-dialog__result p {
  color: #5f5e5b;
}

.ai-screen-dialog__meta,
.ai-screen-dialog__warnings {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0;
  list-style: none;
}

.ai-screen-dialog__meta span,
.ai-screen-dialog__warnings li {
  padding: 4px 8px;
  border-radius: 999px;
  background: #f1f1ef;
  color: #4b4a46;
  font-size: 12px;
}
</style>
