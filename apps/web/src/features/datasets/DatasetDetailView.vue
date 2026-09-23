<script setup lang="ts">
import { Play, Save, Trash2 } from "@lucide/vue";
import { computed, onBeforeUnmount, ref, shallowRef, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { ApiError } from "../../lib/api";
import InlineNotice from "../../ui/InlineNotice.vue";
import { useStudioPermissions } from "../identity/permissions";
import AiAnalysisPanel from "../ai/AiAnalysisPanel.vue";
import { getDatasource } from "../datasources/api";
import { listFileAssets } from "../files/api";
import type { FileAsset } from "../files/types";
import ParameterEditor from "../query/ParameterEditor.vue";
import QueryResultTable from "../query/QueryResultTable.vue";
import SqlEditor from "../query/SqlEditor.vue";
import type {
  JsonValue,
  QueryParameterInput,
  QueryResult,
  SqlDialect,
} from "../query/types";
import {
  deleteDataset,
  getDataset,
  getDatasetProfile,
  previewDataset,
  updateDatasetProfile,
  updateDataset,
} from "./api";
import type {
  Dataset,
  DatasetAggregation,
  DatasetFieldProfile,
  DatasetFieldRole,
  DatasetProfile,
} from "./types";

const route = useRoute();
const router = useRouter();
const { canCreate, canWriteResource } = useStudioPermissions();
const canWrite = ref(false);
const dataset = ref<Dataset | null>(null);
const profile = ref<DatasetProfile | null>(null);
const profileDraft = ref<Record<string, {
  data_type: string;
  role: DatasetFieldRole;
  default_aggregation: DatasetAggregation | "";
  unit: string;
  display_name: string;
}>>({});
const loading = ref(true);
const saving = ref(false);
const previewing = ref(false);
const deleting = ref(false);
const profileSaving = ref(false);
const loadError = ref<ApiError | null>(null);
const formError = ref<ApiError | null>(null);
const previewError = ref<ApiError | null>(null);
const profileError = ref<ApiError | null>(null);
const result = ref<QueryResult | null>(null);
const fileAsset = ref<FileAsset | null>(null);
const name = ref("");
const sql = ref("");
const maxRows = ref(5000);
const timeoutSeconds = ref(30);
const parameters = shallowRef<QueryParameterInput[]>([]);
const parametersValid = ref(true);
let loadController: AbortController | null = null;
let previewController: AbortController | null = null;

const datasourceDialect = ref<SqlDialect>("sqlite");
const isSqlDataset = computed(() => dataset.value?.definition.query.kind === "sql");
const fileFormatLabel = computed(() => {
  if (dataset.value?.definition.query.kind !== "file") {
    return "";
  }
  return dataset.value.definition.query.format.toUpperCase();
});

function hydrate(value: Dataset): void {
  dataset.value = value;
  name.value = value.name;
  sql.value = value.definition.query.kind === "sql"
    ? value.definition.query.sql
    : "";
  maxRows.value = value.definition.max_rows;
  timeoutSeconds.value = value.definition.timeout_seconds;
  parameters.value = value.definition.query.kind === "sql"
    ? value.definition.parameters.map((parameter) => ({
        name: parameter.name,
        data_type: parameter.data_type,
        value: parameter.default,
      }))
    : [];
}

function hydrateProfile(value: DatasetProfile): void {
  profile.value = value;
  profileDraft.value = Object.fromEntries(
    value.fields.map((field) => [field.name, {
      data_type: field.data_type,
      role: field.role,
      default_aggregation: field.default_aggregation ?? "",
      unit: field.unit ?? "",
      display_name: field.display_name ?? field.name,
    }]),
  );
}

async function load(id: string): Promise<void> {
  loadController?.abort();
  const controller = new AbortController();
  loadController = controller;
  loading.value = true;
  loadError.value = null;
  canWrite.value = false;
  profile.value = null;
  profileError.value = null;
  try {
    const [loaded, writable] = await Promise.all([
      getDataset(id, controller.signal), canWriteResource("dataset", id),
    ]);
    const query = loaded.definition.query;
    let nextDialect: SqlDialect = "sqlite";
    let nextFileAsset: FileAsset | null = null;
    if (loaded.data_source_id !== null) {
      const source = await getDatasource(
        loaded.data_source_id,
        controller.signal,
      );
      nextDialect = source.config.type;
    } else if (query.kind === "file") {
      const assets = await listFileAssets(controller.signal);
      nextFileAsset = assets.find(
        (asset) => asset.id === query.asset_id,
      ) ?? null;
    }
    if (!controller.signal.aborted) {
      datasourceDialect.value = nextDialect;
      fileAsset.value = nextFileAsset;
      hydrate(loaded);
      canWrite.value = writable;
      try {
        hydrateProfile(await getDatasetProfile(id, controller.signal));
      } catch (reason) {
        if (!controller.signal.aborted) {
          profileError.value = reason instanceof ApiError
            ? reason
            : new ApiError({
                code: "DATASET_PROFILE_LOAD_FAILED",
                message: "暂时无法加载数据画像。",
                requestId: "",
                status: 500,
              });
        }
      }
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

async function saveProfile(): Promise<void> {
  if (!canWrite.value || dataset.value === null || profile.value === null) {
    return;
  }
  profileSaving.value = true;
  profileError.value = null;
  try {
    const corrections = profile.value.fields.flatMap((field) => {
      const draft = profileDraft.value[field.name] ?? field;
      const typeOrRoleChanged =
        draft.data_type !== field.data_type || draft.role !== field.role;
      const aggregationChanged =
        draft.default_aggregation !== (field.default_aggregation ?? "");
      const unitChanged = draft.unit !== (field.unit ?? "");
      const displayNameChanged =
        draft.display_name !== (field.display_name ?? field.name);
      if (!typeOrRoleChanged && !aggregationChanged && !unitChanged && !displayNameChanged) {
        return [];
      }
      const correction: {
        name: string;
        data_type?: DatasetFieldProfile["data_type"];
        role?: DatasetFieldRole;
        default_aggregation?: DatasetAggregation;
        unit?: string;
        display_name?: string;
      } = {
        name: field.name,
      };
      if (typeOrRoleChanged) {
        correction.data_type = draft.data_type as DatasetFieldProfile["data_type"];
        correction.role = draft.role;
      }
      if (aggregationChanged && draft.default_aggregation !== "") {
        correction.default_aggregation = draft.default_aggregation;
      }
      if (unitChanged && draft.unit !== "") {
        correction.unit = draft.unit;
      }
      if (displayNameChanged && draft.display_name !== "") {
        correction.display_name = draft.display_name;
      }
      return [correction];
    });
    if (corrections.length === 0) {
      profileSaving.value = false;
      return;
    }
    const updated = await updateDatasetProfile(dataset.value.id, {
      fields: corrections,
    });
    hydrateProfile(updated);
  } catch (reason) {
    profileError.value = reason instanceof ApiError
      ? reason
      : new ApiError({
          code: "DATASET_PROFILE_UPDATE_FAILED",
          message: "暂时无法保存字段修正。",
          requestId: "",
          status: 500,
        });
  } finally {
    profileSaving.value = false;
  }
}

async function save(): Promise<void> {
  if (
    !canWrite.value ||
    dataset.value === null ||
    name.value.trim() === "" ||
    !parametersValid.value
  ) {
    return;
  }
  const isSql = dataset.value.definition.query.kind === "sql";
  if (isSql && sql.value.trim() === "") {
    return;
  }
  saving.value = true;
  formError.value = null;
  try {
    const updated = await updateDataset(
      dataset.value.id,
      isSql
        ? {
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
          }
        : {
            name: name.value.trim(),
            max_rows: maxRows.value,
            timeout_seconds: timeoutSeconds.value,
          },
    );
    hydrate(updated);
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

async function remove(): Promise<void> {
  if (
    !canWrite.value ||
    dataset.value === null ||
    deleting.value ||
    !window.confirm(
      `删除“${dataset.value.name}”？此操作无法撤销。来源文件不会自动删除。`,
    )
  ) {
    return;
  }
  deleting.value = true;
  formError.value = null;
  try {
    await deleteDataset(dataset.value.id);
    await router.push("/studio/datasets");
  } catch (reason) {
    formError.value =
      reason instanceof ApiError
        ? reason
        : new ApiError({
            code: "DATASET_DELETE_FAILED",
            message: "暂时无法删除数据集。",
            requestId: "",
            status: 500,
          });
  } finally {
    deleting.value = false;
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
            {{
              isSqlDataset
                ? "编辑查询定义并使用参数预览结果。"
                : "查看文件结构并直接预览解析结果。"
            }}
          </p>
        </div>
        <div class="query-actions">
          <button
            v-if="canWrite"
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
            v-if="canWrite"
            class="secondary-button"
            data-action="delete-dataset"
            type="button"
            :disabled="deleting"
            @click="remove"
          >
            <Trash2 :size="14" aria-hidden="true" />
            {{ deleting ? "正在删除…" : "删除" }}
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

      <InlineNotice v-if="!canWrite" tone="info">当前为只读访问，可调整预览参数并运行查询。</InlineNotice>
      <div v-if="isSqlDataset">
        <div class="dataset-config-grid">
          <label>
            <span>名称</span>
            <input v-model="name" name="name" :disabled="!canWrite" />
          </label>
          <label>
            <span>最大行数</span>
            <input v-model.number="maxRows" name="maxRows" type="number" min="1" max="5000" :disabled="!canWrite" />
          </label>
          <label>
            <span>超时（秒）</span>
            <input v-model.number="timeoutSeconds" name="timeoutSeconds" type="number" min="1" max="300" :disabled="!canWrite" />
          </label>
        </div>

        <div id="dataset-sql-editor" class="sql-editor-frame dataset-sql-editor">
          <SqlEditor v-if="canWrite" v-model="sql" :dialect="datasourceDialect" />
          <pre v-else class="readonly-sql" aria-label="SQL 查询定义">{{ sql }}</pre>
        </div>

        <ParameterEditor
          v-model="parameters"
          :allow-add="false"
          @validity="parametersValid = $event"
        />
      </div>

      <div v-else-if="dataset.definition.query.kind === 'file'" class="dataset-file-detail">
        <div class="dataset-config-grid dataset-config-grid--stacked">
          <label>
            <span>名称</span>
            <input v-model="name" name="name" :disabled="!canWrite" />
          </label>
          <label>
            <span>来源文件</span>
            <input :value="fileAsset?.original_name ?? dataset.definition.query.asset_id" disabled />
          </label>
          <label>
            <span>格式</span>
            <input :value="fileFormatLabel" disabled />
          </label>
          <label v-if="dataset.definition.query.sheet_name">
            <span>Excel Sheet</span>
            <input :value="dataset.definition.query.sheet_name" disabled />
          </label>
          <label>
            <span>最大行数</span>
            <input v-model.number="maxRows" name="maxRows" type="number" min="1" max="5000" :disabled="!canWrite" />
          </label>
          <label>
            <span>超时（秒）</span>
            <input v-model.number="timeoutSeconds" name="timeoutSeconds" type="number" min="1" max="300" :disabled="!canWrite" />
          </label>
        </div>
        <div v-if="fileAsset" class="dataset-file-asset">
          <div class="dataset-file-asset__header">
            <strong>{{ fileAsset.original_name }}</strong>
            <span class="type-pill">{{ fileFormatLabel }}</span>
          </div>
          <p>
            {{ fileAsset.row_count.toLocaleString("zh-CN") }} 行 ·
            {{ fileAsset.fields.length }} 个字段
          </p>
          <ul class="dataset-file-fields">
            <li v-for="field in fileAsset.fields" :key="field.name">
              <code>{{ field.name }}</code>
              <span>{{ field.data_type }}</span>
            </li>
          </ul>
        </div>
      </div>

      <section v-if="profile" class="dataset-profile" aria-labelledby="dataset-profile-title">
        <div class="dataset-profile__heading">
          <div>
            <p class="page-eyebrow">Profile</p>
            <h2 id="dataset-profile-title">数据画像</h2>
            <p>
              {{ profile.row_count.toLocaleString("zh-CN") }} 行 ·
              {{ profile.fields.length }} 个字段
              <span v-if="profile.sampled">· 基于受限样本</span>
            </p>
          </div>
          <button
            v-if="canWrite"
            class="secondary-button"
            data-action="save-profile"
            type="button"
            :disabled="profileSaving"
            @click="saveProfile"
          >
            <Save :size="14" aria-hidden="true" />
            {{ profileSaving ? "正在保存…" : "保存字段修正" }}
          </button>
        </div>
        <div class="dataset-profile__table-wrap">
          <table class="dataset-profile__table">
            <thead>
              <tr><th>字段</th><th>类型</th><th>角色</th><th>聚合</th><th>单位</th><th>显示名</th><th>基数</th><th>空值</th></tr>
            </thead>
            <tbody>
              <tr v-for="field in profile.fields" :key="field.name">
                <th scope="row"><code>{{ field.name }}</code></th>
                <td>
                  <select
                    v-if="canWrite"
                    :data-profile-type="field.name"
                    v-model="profileDraft[field.name]!.data_type"
                  >
                    <option value="string">string</option>
                    <option value="integer">integer</option>
                    <option value="number">number</option>
                    <option value="boolean">boolean</option>
                    <option value="date">date</option>
                    <option value="datetime">datetime</option>
                  </select>
                  <span v-else>{{ field.data_type }}</span>
                </td>
                <td>
                  <select
                    v-if="canWrite"
                    :data-profile-role="field.name"
                    v-model="profileDraft[field.name]!.role"
                  >
                    <option value="identifier">标识</option>
                    <option value="dimension">维度</option>
                    <option value="measure">度量</option>
                    <option value="geography">地理</option>
                    <option value="temporal">时间</option>
                    <option value="text">文本</option>
                    <option value="boolean">布尔</option>
                    <option value="unknown">未知</option>
                  </select>
                  <span v-else>{{ field.role }}</span>
                </td>
                <td>
                  <select
                    v-if="canWrite"
                    :data-profile-aggregation="field.name"
                    v-model="profileDraft[field.name]!.default_aggregation"
                  >
                    <option value="">无</option>
                    <option value="sum">sum</option>
                    <option value="avg">avg</option>
                    <option value="min">min</option>
                    <option value="max">max</option>
                    <option value="count">count</option>
                  </select>
                  <span v-else>{{ field.default_aggregation || "-" }}</span>
                </td>
                <td>
                  <input
                    v-if="canWrite"
                    :data-profile-unit="field.name"
                    v-model="profileDraft[field.name]!.unit"
                  />
                  <span v-else>{{ field.unit || "-" }}</span>
                </td>
                <td>
                  <input
                    v-if="canWrite"
                    :data-profile-display-name="field.name"
                    v-model="profileDraft[field.name]!.display_name"
                  />
                  <span v-else>{{ field.display_name || field.name }}</span>
                </td>
                <td>{{ field.cardinality }}</td>
                <td>{{ field.null_count }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
      <InlineNotice v-if="profileError" tone="error">
        <p>{{ profileError.message }}</p>
        <code v-if="profileError.requestId">{{ profileError.requestId }}</code>
      </InlineNotice>

      <InlineNotice v-if="formError" tone="error">
        <p>{{ formError.message }}</p>
        <code v-if="formError.requestId">{{ formError.requestId }}</code>
      </InlineNotice>
      <InlineNotice v-if="previewError" tone="error">
        <p>{{ previewError.message }}</p>
        <code v-if="previewError.requestId">{{ previewError.requestId }}</code>
      </InlineNotice>

      <AiAnalysisPanel
        v-if="canCreate"
        class="dataset-ai-panel"
        :fixed-dataset-id="dataset.id"
      />

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

<style scoped>
.readonly-sql {
  margin: 0;
  padding: 14px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.dataset-ai-panel {
  margin-top: 20px;
}
.dataset-profile {
  margin-top: 20px;
  border: 1px solid var(--border-color, #d6dde7);
  padding: 16px;
}
.dataset-profile__heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.dataset-profile__heading h2,
.dataset-profile__heading p {
  margin: 0;
}
.dataset-profile__table-wrap {
  overflow-x: auto;
  margin-top: 12px;
}
.dataset-profile__table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}
.dataset-profile__table th,
.dataset-profile__table td {
  border-bottom: 1px solid var(--border-color, #d6dde7);
  padding: 8px;
  white-space: nowrap;
}
</style>
