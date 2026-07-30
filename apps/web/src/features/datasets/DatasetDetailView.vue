<script setup lang="ts">
import { Play, Save } from "@lucide/vue";
import { onBeforeUnmount, ref, shallowRef, watch } from "vue";
import { useRoute } from "vue-router";

import { ApiError } from "../../lib/api";
import InlineNotice from "../../ui/InlineNotice.vue";
import { getDatasource } from "../datasources/api";
import ParameterEditor from "../query/ParameterEditor.vue";
import QueryResultTable from "../query/QueryResultTable.vue";
import SqlEditor from "../query/SqlEditor.vue";
import type {
  JsonValue,
  QueryParameterInput,
  QueryResult,
  SqlDialect,
} from "../query/types";
import { getDataset, previewDataset, updateDataset } from "./api";
import type { Dataset } from "./types";

const route = useRoute();
const dataset = ref<Dataset | null>(null);
const loading = ref(true);
const saving = ref(false);
const previewing = ref(false);
const loadError = ref<ApiError | null>(null);
const formError = ref<ApiError | null>(null);
const previewError = ref<ApiError | null>(null);
const result = ref<QueryResult | null>(null);
const name = ref("");
const sql = ref("");
const maxRows = ref(5000);
const timeoutSeconds = ref(30);
const parameters = shallowRef<QueryParameterInput[]>([]);
const parametersValid = ref(true);
let loadController: AbortController | null = null;
let previewController: AbortController | null = null;

const datasourceDialect = ref<SqlDialect>("sqlite");

function hydrate(value: Dataset): void {
  dataset.value = value;
  name.value = value.name;
  sql.value = value.definition.query.kind === "sql"
    ? value.definition.query.sql
    : "";
  maxRows.value = value.definition.max_rows;
  timeoutSeconds.value = value.definition.timeout_seconds;
  parameters.value = value.definition.parameters.map((parameter) => ({
    name: parameter.name,
    data_type: parameter.data_type,
    value: parameter.default,
  }));
}

async function load(id: string): Promise<void> {
  loadController?.abort();
  const controller = new AbortController();
  loadController = controller;
  loading.value = true;
  loadError.value = null;
  try {
    const loaded = await getDataset(id, controller.signal);
    const source = await getDatasource(
      loaded.data_source_id,
      controller.signal,
    );
    if (!controller.signal.aborted) {
      datasourceDialect.value = source.config.type;
      hydrate(loaded);
    }
  } catch (reason) {
    if (!controller.signal.aborted) {
      loadError.value =
        reason instanceof ApiError
          ? reason
          : new ApiError({
              code: "DATASET_LOAD_FAILED",
              message: "暂时无法加载数据集。",
              requestId: "",
              status: 500,
            });
    }
  } finally {
    if (!controller.signal.aborted) {
      loading.value = false;
    }
  }
}

async function save(): Promise<void> {
  if (
    dataset.value === null ||
    name.value.trim() === "" ||
    sql.value.trim() === "" ||
    !parametersValid.value
  ) {
    return;
  }
  saving.value = true;
  formError.value = null;
  try {
    const updated = await updateDataset(dataset.value.id, {
      name: name.value.trim(),
      sql: sql.value,
      parameters: parameters.value.map((parameter) => ({
        name: parameter.name.trim(),
        data_type: parameter.data_type,
        required: false,
        default: parameter.value,
      })),
      max_rows: maxRows.value,
      timeout_seconds: timeoutSeconds.value,
    });
    dataset.value = updated;
  } catch (reason) {
    formError.value =
      reason instanceof ApiError
        ? reason
        : new ApiError({
            code: "DATASET_UPDATE_FAILED",
            message: "暂时无法保存数据集。",
            requestId: "",
            status: 500,
          });
  } finally {
    saving.value = false;
  }
}

async function preview(): Promise<void> {
  if (dataset.value === null || !parametersValid.value) {
    return;
  }
  previewController?.abort();
  const controller = new AbortController();
  previewController = controller;
  previewing.value = true;
  previewError.value = null;
  result.value = null;
  const values: Record<string, JsonValue> = Object.fromEntries(
    parameters.value.map((parameter) => [
      parameter.name.trim(),
      parameter.value,
    ]),
  );
  try {
    const response = await previewDataset(
      dataset.value.id,
      { parameters: values },
      controller.signal,
    );
    if (!controller.signal.aborted) {
      result.value = response;
    }
  } catch (reason) {
    if (!controller.signal.aborted) {
      previewError.value =
        reason instanceof ApiError
          ? reason
          : new ApiError({
              code: "DATASET_PREVIEW_FAILED",
              message: "预览失败，请稍后重试。",
              requestId: "",
              status: 500,
            });
    }
  } finally {
    if (!controller.signal.aborted) {
      previewing.value = false;
    }
  }
}

watch(
  () => String(route.params.id ?? ""),
  (id) => void load(id),
  { immediate: true },
);

onBeforeUnmount(() => {
  loadController?.abort();
  previewController?.abort();
});
</script>

<template>
  <section class="page-column dataset-detail-page" aria-labelledby="dataset-detail-title">
    <p v-if="loading" class="loading-copy" role="status">正在加载数据集…</p>
    <InlineNotice v-else-if="loadError" tone="error">
      <p>{{ loadError.message }}</p>
      <code v-if="loadError.requestId">{{ loadError.requestId }}</code>
    </InlineNotice>

    <template v-else-if="dataset">
      <div class="page-heading dataset-detail-heading">
        <div>
          <p class="page-eyebrow">Dataset · {{ dataset.id }}</p>
          <h1 id="dataset-detail-title">{{ dataset.name }}</h1>
          <p class="page-description">
            编辑查询定义并使用参数预览结果。
          </p>
        </div>
        <div class="query-actions">
          <button
            class="secondary-button"
            data-action="save-dataset"
            type="button"
            :disabled="saving"
            @click="save"
          >
            <Save :size="14" aria-hidden="true" />
            {{ saving ? "正在保存…" : "保存" }}
          </button>
          <button
            class="primary-button"
            data-action="preview-dataset"
            type="button"
            :disabled="previewing || !parametersValid"
            @click="preview"
          >
            <Play :size="14" aria-hidden="true" />
            {{ previewing ? "正在预览…" : "运行预览" }}
          </button>
        </div>
      </div>

      <div class="dataset-config-grid">
        <label>
          <span>名称</span>
          <input v-model="name" name="name" />
        </label>
        <label>
          <span>最大行数</span>
          <input v-model.number="maxRows" name="maxRows" type="number" min="1" max="5000" />
        </label>
        <label>
          <span>超时（秒）</span>
          <input v-model.number="timeoutSeconds" name="timeoutSeconds" type="number" min="1" max="300" />
        </label>
      </div>

      <div class="sql-editor-frame dataset-sql-editor">
        <SqlEditor v-model="sql" :dialect="datasourceDialect" />
      </div>

      <ParameterEditor
        v-model="parameters"
        :allow-add="false"
        @validity="parametersValid = $event"
      />

      <InlineNotice v-if="formError" tone="error">
        <p>{{ formError.message }}</p>
        <code v-if="formError.requestId">{{ formError.requestId }}</code>
      </InlineNotice>
      <InlineNotice v-if="previewError" tone="error">
        <p>{{ previewError.message }}</p>
        <code v-if="previewError.requestId">{{ previewError.requestId }}</code>
      </InlineNotice>

      <div v-if="result" class="query-result-panel">
        <div class="result-summary">
          <strong>{{ result.row_count.toLocaleString("zh-CN") }} 行</strong>
          <span>{{ result.duration_ms.toLocaleString("zh-CN") }} ms</span>
          <code>{{ result.request_id }}</code>
        </div>
        <QueryResultTable :result="result" />
      </div>
    </template>
  </section>
</template>
