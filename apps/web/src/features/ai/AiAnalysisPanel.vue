<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import { ApiError } from "../../lib/api";
import InlineNotice from "../../ui/InlineNotice.vue";
import { listDatasets } from "../datasets/api";
import type { Dataset } from "../datasets/types";
import type { JsonValue } from "../query/types";
import ChartSuggestionCard from "./ChartSuggestionCard.vue";
import { analyzeAi, getAiStatus } from "./api";
import type { AiAnalysisResponse, AiChartResponse, AiHealth } from "./types";

const props = withDefaults(
  defineProps<{
    fixedDatasetId?: string;
    initialDatasetId?: string;
    targetComponentType?: AiChartResponse["chart_spec"]["visual"]["type"];
    currentProps?: Record<string, JsonValue>;
    applyLabel?: string;
    canApply?: boolean;
  }>(),
  {
    fixedDatasetId: undefined,
    initialDatasetId: "",
    targetComponentType: undefined,
    currentProps: undefined,
    applyLabel: "应用图表建议",
    canApply: false,
  },
);

const emit = defineEmits<{
  "apply-chart": [chartSpec: AiChartResponse["chart_spec"]];
}>();

const datasets = ref<Dataset[]>([]);
const loadingDatasets = ref(false);
const datasetError = ref<ApiError | null>(null);
const generateError = ref<ApiError | null>(null);
const formError = ref("");
const generating = ref(false);
const question = ref("");
const datasetId = ref(props.fixedDatasetId ?? props.initialDatasetId);
const analysis = ref<AiAnalysisResponse | null>(null);
const chart = ref<AiChartResponse | null>(null);
const aiStatus = ref<AiHealth | null>(null);

const effectiveDatasetId = computed(() => props.fixedDatasetId ?? datasetId.value);
const selectedDataset = computed(() =>
  datasets.value.find((item) => item.id === effectiveDatasetId.value) ?? null,
);

watch(
  () => props.fixedDatasetId,
  (fixedDatasetId) => {
    datasetId.value = fixedDatasetId ?? props.initialDatasetId;
  },
  { immediate: true },
);

watch([effectiveDatasetId, question], () => {
  analysis.value = null;
  chart.value = null;
  generateError.value = null;
});

watch(
  () => props.initialDatasetId,
  (initialDatasetId) => {
    if (!props.fixedDatasetId) {
      datasetId.value = initialDatasetId;
    }
  },
);

async function loadDatasetOptions(): Promise<void> {
  if (props.fixedDatasetId) {
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

async function submit(): Promise<void> {
  const nextDatasetId = effectiveDatasetId.value.trim();
  const nextQuestion = question.value.trim();
  if (!nextDatasetId || !nextQuestion) {
    formError.value = "请选择数据集并输入分析问题。";
    return;
  }
  generating.value = true;
  formError.value = "";
  generateError.value = null;
  analysis.value = null;
  chart.value = null;
  try {
    const nextAnalysis = await analyzeAi({
      question: nextQuestion,
      dataset_ids: [nextDatasetId],
      mode: "chart",
    });
    analysis.value = nextAnalysis;
    chart.value = nextAnalysis.chart_spec
      ? {
          chart_spec: nextAnalysis.chart_spec,
          explanation: nextAnalysis.narrative,
          preview: nextAnalysis.preview,
          warnings: nextAnalysis.warnings,
        }
      : null;
  } catch (reason) {
    generateError.value =
      reason instanceof ApiError
        ? reason
        : new ApiError({
            code: "AI_ANALYSIS_FAILED",
            message: "暂时无法生成 AI 建议。",
            requestId: "",
            status: 500,
          });
  } finally {
    generating.value = false;
  }
}

onMounted(() => void loadDatasetOptions());
onMounted(async () => {
  try {
    aiStatus.value = await getAiStatus();
  } catch {
    aiStatus.value = null;
  }
});
</script>

<template>
  <section class="ai-panel" aria-label="AI 分析面板">
    <header class="ai-panel__header">
      <div>
        <h2>AI 分析</h2>
        <p>
          {{ fixedDatasetId ? "围绕当前数据集生成分析和图表建议。" : "选择数据集后生成分析和图表建议。" }}
        </p>
      </div>
      <code v-if="fixedDatasetId">{{ fixedDatasetId }}</code>
    </header>

    <InlineNotice v-if="datasetError" tone="error">
      <p>{{ datasetError.message }}</p>
      <code v-if="datasetError.requestId">{{ datasetError.requestId }}</code>
    </InlineNotice>
    <InlineNotice v-if="generateError" tone="error">
      <p>{{ generateError.message }}</p>
      <code v-if="generateError.requestId">{{ generateError.requestId }}</code>
    </InlineNotice>
    <InlineNotice v-if="aiStatus?.status === 'unconfigured'" tone="info">
      <p>AI 服务尚未配置，可使用下方 SQL 编辑器手动查询和分析。</p>
      <a v-if="fixedDatasetId" href="#dataset-sql-editor">前往 SQL 编辑器</a>
    </InlineNotice>

    <form class="ai-panel__form" @submit.prevent="submit">
      <label v-if="!fixedDatasetId" class="ai-panel__field">
        <span>数据集</span>
        <select
          v-model="datasetId"
          name="aiDatasetId"
          :disabled="loadingDatasets || generating"
        >
          <option value="">
            {{ loadingDatasets ? "正在加载数据集…" : "请选择数据集" }}
          </option>
          <option
            v-for="item in datasets"
            :key="item.id"
            :value="item.id"
          >
            {{ item.name }}
          </option>
        </select>
      </label>

      <label class="ai-panel__field ai-panel__field--wide">
        <span>分析问题</span>
        <textarea
          v-model="question"
          name="aiQuestion"
          rows="4"
          :disabled="generating"
          placeholder="例如：帮我找出销售额变化最大的维度，并推荐最合适的可视化方式。"
          @input="formError = ''"
        />
      </label>

      <p v-if="formError" class="ai-panel__error">{{ formError }}</p>

      <div class="ai-panel__actions">
        <span v-if="selectedDataset" class="ai-panel__dataset-name">
          当前数据集：{{ selectedDataset.name }}
        </span>
        <button class="primary-button" type="submit" :disabled="generating">
          {{ generating ? "正在生成…" : "生成建议" }}
        </button>
      </div>
    </form>

    <section v-if="analysis" class="ai-panel__result" aria-label="AI 分析结果">
      <div class="ai-panel__copy">
        <h3>分析结论</h3>
        <p>{{ analysis.narrative }}</p>
      </div>

      <div class="ai-panel__plan">
        <span>推荐图表 {{ analysis.plan.recommended_chart }}</span>
        <span>维度 {{ analysis.plan.dimensions?.length ?? 0 }}</span>
        <span>指标 {{ analysis.plan.measures?.length ?? 0 }}</span>
        <span v-if="analysis.plan.requires_confirmation">需要确认</span>
      </div>

      <ul
        v-if="analysis.warnings.length > 0"
        class="ai-panel__warnings"
        aria-label="分析警告"
      >
        <li v-for="warning in analysis.warnings" :key="warning">
          {{ warning }}
        </li>
      </ul>
    </section>

    <ChartSuggestionCard
      v-if="chart"
      :response="chart"
      :current-props="currentProps"
      :apply-label="applyLabel"
      :can-apply="canApply"
      @apply-chart="emit('apply-chart', $event)"
    />
  </section>
</template>

<style scoped>
.ai-panel {
  display: grid;
  gap: 14px;
  padding: 16px;
  border: 1px solid var(--dp-border-strong);
  border-radius: 16px;
  background: #fff;
}

.ai-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.ai-panel__header h2,
.ai-panel__header p,
.ai-panel__copy h3,
.ai-panel__copy p,
.ai-panel__warnings {
  margin: 0;
}

.ai-panel h2,
.ai-panel h3 {
  color: var(--dp-text);
}

.ai-panel__header p,
.ai-panel__copy p {
  color: #5f5e5b;
}

.ai-panel__form {
  display: grid;
  gap: 12px;
}

.ai-panel__field {
  display: grid;
  gap: 6px;
}

.ai-panel__field span,
.ai-panel__dataset-name {
  color: var(--dp-text);
  font-size: 13px;
}

.ai-panel__field textarea,
.ai-panel__field select {
  box-sizing: border-box;
  width: 100%;
}

.ai-panel__field textarea::placeholder {
  color: #6b6a67;
}

.ai-panel__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.ai-panel__error {
  margin: 0;
  color: #b42318;
  font-size: 13px;
}

.ai-panel__result {
  display: grid;
  gap: 10px;
}

.ai-panel__plan,
.ai-panel__warnings {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0;
  list-style: none;
}

.ai-panel__plan span,
.ai-panel__warnings li {
  padding: 4px 8px;
  border-radius: 999px;
  background: #f1f1ef;
  color: #4b4a46;
  font-size: 12px;
}
</style>
