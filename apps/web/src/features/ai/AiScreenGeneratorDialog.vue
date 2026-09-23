<script setup lang="ts">
import { X } from "@lucide/vue";
import { computed, ref, shallowRef, watch } from "vue";

import { ApiError } from "../../lib/api";
import InlineNotice from "../../ui/InlineNotice.vue";
import { listDatasets } from "../datasets/api";
import type { Dataset } from "../datasets/types";
import { compileDashboardPlan } from "../screens/api";
import { editScreen, generateScreen, getAiStatus } from "./api";
import DashboardPlanEditor from "./DashboardPlanEditor.vue";
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
const compilingPlan = ref(false);
const editingPlan = ref(false);
const screenName = ref("");
const question = ref("");
const selectedDatasetIds = ref<string[]>([]);
const datasetSearch = ref("");
const result = shallowRef<AiScreenResponse | null>(null);
const aiStatus = ref<AiHealth | null>(null);
const editQuestion = ref("");
const editScope = ref<"screen" | "regions">("screen");
const selectedEditRegionIds = ref<string[]>([]);
const editFormError = ref("");

function datasetSource(dataset: Dataset): {
  id: string;
  label: string;
  search: string;
} {
  const definition = dataset.definition;
  const query = definition?.query;
  if (query?.kind === "file") {
    return {
      id: `file:${query.asset_id}`,
      label: `文件 · ${query.asset_id}`,
      search: `${query.asset_id} ${query.format}`,
    };
  }
  if (query?.kind === "rest") {
    const source = dataset.data_source_id ?? new URL(query.url).origin;
    return {
      id: `rest:${source}`,
      label: `HTTP API · ${source}`,
      search: `${source} ${query.url}`,
    };
  }
  const source = dataset.data_source_id ?? "未关联来源";
  return {
    id: `database:${source}`,
    label: `数据库 · ${source}`,
    search: source,
  };
}

const datasetGroups = computed(() => {
  const query = datasetSearch.value.trim().toLocaleLowerCase();
  const groups = new Map<
    string,
    { id: string; label: string; datasets: Dataset[] }
  >();
  for (const dataset of datasets.value) {
    const source = datasetSource(dataset);
    const matchesQuery =
      !query ||
      dataset.name.toLocaleLowerCase().includes(query) ||
      dataset.id.toLocaleLowerCase().includes(query) ||
      source.search.toLocaleLowerCase().includes(query);
    if (!matchesQuery) {
      continue;
    }
    const group = groups.get(source.id) ?? {
      id: source.id,
      label: source.label,
      datasets: [],
    };
    group.datasets.push(dataset);
    groups.set(source.id, group);
  }
  return [...groups.values()];
});

const canClose = computed(
  () =>
    !generating.value &&
    !compilingPlan.value &&
    !editingPlan.value &&
    !props.submitting,
);

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
  datasetSearch.value = "";
  formError.value = "";
  generateError.value = null;
  compilingPlan.value = false;
  editingPlan.value = false;
  editQuestion.value = "";
  editScope.value = "screen";
  selectedEditRegionIds.value = [];
  editFormError.value = "";
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
    editQuestion.value = "";
    editScope.value = "screen";
    selectedEditRegionIds.value = [];
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
  if (
    !result.value ||
    props.submitting ||
    compilingPlan.value ||
    editingPlan.value
  ) {
    return;
  }
  emit("confirm", {
    name: screenName.value.trim(),
    result: result.value as AiScreenResponse,
  });
}

async function submitEdit(): Promise<void> {
  if (!result.value) {
    return;
  }
  const prompt = editQuestion.value.trim();
  const affectedRegionIds =
    editScope.value === "regions" ? selectedEditRegionIds.value : [];
  if (!prompt) {
    editFormError.value = "请输入修改要求。";
    return;
  }
  if (editScope.value === "regions" && affectedRegionIds.length === 0) {
    editFormError.value = "请至少选择一个分区。";
    return;
  }
  editingPlan.value = true;
  editFormError.value = "";
  generateError.value = null;
  try {
    const edited = await editScreen({
      question: prompt,
      plan: result.value.plan,
      document: result.value.document,
      affected_region_ids: affectedRegionIds,
    });
    result.value = {
      ...result.value,
      plan: edited.plan,
      document: edited.document,
      report: edited.report,
      explanation: edited.explanation,
      warnings: edited.warnings,
    };
    editQuestion.value = "";
  } catch (reason) {
    generateError.value =
      reason instanceof ApiError
        ? reason
        : new ApiError({
            code: "AI_SCREEN_EDIT_FAILED",
            message: "暂时无法应用大屏修改。",
            requestId: "",
            status: 500,
          });
  } finally {
    editingPlan.value = false;
  }
}

async function updatePlan(plan: AiScreenResponse["plan"]): Promise<void> {
  if (!result.value) {
    return;
  }
  compilingPlan.value = true;
  generateError.value = null;
  try {
    const compiled = await compileDashboardPlan({
      plan,
      canvas_width: result.value.document.canvas.width,
      canvas_height: result.value.document.canvas.height,
    });
    result.value = {
      ...result.value,
      plan: compiled.plan,
      document: compiled.document,
      report: compiled.report ?? result.value.report,
      warnings: compiled.warnings,
    };
  } catch (reason) {
    generateError.value =
      reason instanceof ApiError
        ? reason
        : new ApiError({
            code: "PLAN_COMPILE_FAILED",
            message: "暂时无法应用规划修改。",
            requestId: "",
            status: 500,
          });
  } finally {
    compilingPlan.value = false;
  }
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
        <ul
          v-if="generateError.fieldErrors.length > 0"
          class="ai-screen-dialog__field-errors"
          aria-label="AI 生成错误详情"
        >
          <li v-for="(issue, index) in generateError.fieldErrors" :key="`${issue.component_id ?? 'screen'}-${issue.field}-${index}`">
            <strong v-if="issue.component_id">组件 {{ issue.component_id }}</strong>
            <code v-if="issue.field">{{ issue.field }}</code>
            <span>{{ issue.reason ?? issue.message }}</span>
            <small v-if="issue.expected">期望：{{ issue.expected }}</small>
          </li>
        </ul>
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
            <label class="ai-screen-dialog__dataset-search">
              <span>检索数据集</span>
              <input
                v-model="datasetSearch"
                name="aiScreenDatasetSearch"
                type="search"
                autocomplete="off"
                placeholder="名称或 ID"
                :disabled="generating || submitting"
              />
            </label>
            <p v-if="datasetGroups.length === 0" class="ai-screen-dialog__hint">
              没有匹配的数据集。
            </p>
            <section
              v-for="group in datasetGroups"
              :key="group.id"
              class="ai-screen-dialog__dataset-group"
              :data-source-group="group.id"
              :aria-label="`${group.label}数据集`"
            >
              <h3>{{ group.label }}</h3>
              <label
                v-for="dataset in group.datasets"
                :key="dataset.id"
                class="ai-screen-dialog__dataset-option"
                :data-dataset-id="dataset.id"
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
            </section>
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
        <DashboardPlanEditor
          :model-value="result.plan"
          @update:model-value="updatePlan"
        />
        <form
          class="ai-screen-dialog__edit"
          aria-label="AI 修改大屏草稿"
          @submit.prevent="submitEdit"
        >
          <label class="form-field">
            <span class="form-field__heading">修改要求</span>
            <textarea
              v-model="editQuestion"
              name="aiScreenEditQuestion"
              rows="3"
              placeholder="例如：切换为浅色风格，或把趋势分区改成柱状图。"
              :disabled="editingPlan || compilingPlan || submitting"
              @input="editFormError = ''"
            />
          </label>
          <label class="form-field">
            <span class="form-field__heading">修改范围</span>
            <select
              v-model="editScope"
              name="aiScreenEditScope"
              :disabled="editingPlan || compilingPlan || submitting"
              @change="editFormError = ''"
            >
              <option value="screen">整屏</option>
              <option value="regions">指定分区</option>
            </select>
          </label>
          <fieldset
            v-if="editScope === 'regions'"
            class="ai-screen-dialog__regions"
          >
            <legend>受影响分区</legend>
            <label
              v-for="region in result.plan.regions"
              :key="region.id"
              class="ai-screen-dialog__region-option"
            >
              <input
                v-model="selectedEditRegionIds"
                type="checkbox"
                name="aiScreenEditRegions"
                :value="region.id"
                :disabled="editingPlan || compilingPlan || submitting"
                @change="editFormError = ''"
              />
              <span>{{ region.title || region.id }}</span>
            </label>
          </fieldset>
          <span v-if="editFormError" class="form-field__error">
            {{ editFormError }}
          </span>
          <div class="dialog-actions">
            <button
              class="secondary-button"
              type="submit"
              data-action="edit-ai-screen"
              :disabled="editingPlan || compilingPlan || submitting"
            >
              {{ editingPlan ? "正在修改…" : "应用修改" }}
            </button>
          </div>
        </form>
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
          v-if="(result.report.issues?.length ?? 0) > 0"
          class="ai-screen-dialog__issues"
          aria-label="草稿自检问题"
        >
          <li
            v-for="issue in result.report.issues ?? []"
            :key="`${issue.code}-${issue.component_id ?? 'screen'}-${issue.field}`"
          >
            <strong v-if="issue.component_id">组件 {{ issue.component_id }}</strong>
            <code>{{ issue.field }}</code>
            <span>{{ issue.message }}</span>
          </li>
        </ul>
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
            :aria-busy="compilingPlan || editingPlan"
            :disabled="submitting || compilingPlan || editingPlan"
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

.ai-screen-dialog__edit,
.ai-screen-dialog__regions {
  display: grid;
  gap: 10px;
}

.ai-screen-dialog__edit {
  padding: 12px 0;
  border-block: 1px solid var(--dp-border);
}

.ai-screen-dialog__regions {
  padding: 10px;
  border: 1px solid var(--dp-border);
  border-radius: 8px;
}

.ai-screen-dialog__regions legend {
  padding: 0 6px;
  color: #5f5e5b;
  font-size: 12px;
}

.ai-screen-dialog__region-option {
  display: flex;
  align-items: center;
  gap: 8px;
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

.ai-screen-dialog__dataset-search,
.ai-screen-dialog__dataset-group {
  display: grid;
  gap: 8px;
}

.ai-screen-dialog__dataset-search span,
.ai-screen-dialog__dataset-group h3 {
  margin: 0;
  color: #5f5e5b;
  font-size: 12px;
  font-weight: 600;
}

.ai-screen-dialog__dataset-search input {
  width: 100%;
}

.ai-screen-dialog__dataset-group + .ai-screen-dialog__dataset-group {
  padding-top: 10px;
  border-top: 1px solid var(--dp-border);
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
.ai-screen-dialog__issues,
.ai-screen-dialog__warnings {
  margin: 0;
}

.ai-screen-dialog__field-errors {
  display: grid;
  gap: 6px;
  margin: 8px 0 0;
  padding-left: 18px;
}

.ai-screen-dialog__field-errors li {
  display: grid;
  gap: 2px;
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
.ai-screen-dialog__issues li,
.ai-screen-dialog__warnings li {
  padding: 4px 8px;
  border-radius: 999px;
  background: #f1f1ef;
  color: #4b4a46;
  font-size: 12px;
}
</style>
