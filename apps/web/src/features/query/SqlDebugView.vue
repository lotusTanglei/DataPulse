<script setup lang="ts">
import { Play, Save } from "@lucide/vue";
import { computed, onBeforeUnmount, ref, shallowRef } from "vue";

import { ApiError } from "../../lib/api";
import InlineNotice from "../../ui/InlineNotice.vue";
import { useStudioPermissions } from "../identity/permissions";
import SaveDatasetDialog from "../datasets/SaveDatasetDialog.vue";
import SchemaBrowser from "../datasources/SchemaBrowser.vue";
import type { Datasource } from "../datasources/types";
import { runDatasourceQuery } from "./api";
import ParameterEditor from "./ParameterEditor.vue";
import QueryResultTable from "./QueryResultTable.vue";
import SqlEditor from "./SqlEditor.vue";
import type {
  JsonValue,
  QueryParameterInput,
  QueryResult,
} from "./types";

const props = defineProps<{ datasource: Datasource }>();
const { canCreate } = useStudioPermissions();

const sql = ref("SELECT *\nFROM ");
const parameters = shallowRef<QueryParameterInput[]>([]);
const parametersValid = ref(true);
const running = ref(false);
const result = ref<QueryResult | null>(null);
const error = ref<ApiError | null>(null);
const saveDialogOpen = ref(false);
let queryController: AbortController | null = null;

const parameterPayload = computed<Record<string, JsonValue>>(() =>
  Object.fromEntries(
    parameters.value.map((parameter) => [
      parameter.name.trim(),
      parameter.value,
    ]),
  ),
);

async function run(): Promise<void> {
  if (sql.value.trim() === "" || !parametersValid.value) {
    return;
  }
  queryController?.abort();
  const controller = new AbortController();
  queryController = controller;
  running.value = true;
  error.value = null;
  result.value = null;
  try {
    const response = await runDatasourceQuery(
      props.datasource.id,
      {
        sql: sql.value,
        parameters: parameterPayload.value,
        max_rows: 5000,
        timeout_seconds: 30,
      },
      controller.signal,
    );
    if (!controller.signal.aborted) {
      result.value = response;
    }
  } catch (reason) {
    if (!controller.signal.aborted) {
      error.value =
        reason instanceof ApiError
          ? reason
          : new ApiError({
              code: "QUERY_FAILED",
              message: "查询执行失败，请稍后重试。",
              requestId: "",
              status: 500,
            });
    }
  } finally {
    if (!controller.signal.aborted) {
      running.value = false;
    }
  }
}

onBeforeUnmount(() => queryController?.abort());
</script>

<template>
  <div class="sql-debug-workspace">
    <aside class="sql-schema-panel">
      <SchemaBrowser :datasource="datasource" />
    </aside>

    <section class="sql-workbench" aria-label="SQL 调试工作区">
      <div class="sql-toolbar">
        <div class="query-policy">
          <span class="policy-badge">只读查询</span>
          <span>超时 30 秒</span>
          <span>最多 5,000 行</span>
        </div>
        <div class="query-actions">
          <button
            v-if="result && canCreate"
            class="secondary-button"
            type="button"
            @click="saveDialogOpen = true"
          >
            <Save :size="14" aria-hidden="true" />
            保存为数据集
          </button>
          <button
            class="primary-button"
            data-action="run-query"
            type="button"
            :aria-busy="running"
            :disabled="sql.trim() === '' || !parametersValid"
            @click="run"
          >
            <Play :size="14" aria-hidden="true" />
            {{ running ? "正在运行…" : "运行" }}
          </button>
        </div>
      </div>

      <div class="sql-editor-frame">
        <SqlEditor
          v-model="sql"
          :dialect="datasource.config.type"
          @run="run"
        />
      </div>

      <ParameterEditor
        v-model="parameters"
        @validity="parametersValid = $event"
      />

      <InlineNotice v-if="error" tone="error">
        <p>{{ error.message }}</p>
        <code>{{ error.code }}</code>
        <code v-if="error.requestId">{{ error.requestId }}</code>
      </InlineNotice>

      <div v-if="result" class="query-result-panel">
        <div class="result-summary">
          <strong>{{ result.row_count.toLocaleString("zh-CN") }} 行</strong>
          <span>{{ result.duration_ms.toLocaleString("zh-CN") }} ms</span>
          <span v-if="result.truncated">已截断</span>
          <code v-if="result.request_id">{{ result.request_id }}</code>
        </div>
        <QueryResultTable :result="result" />
      </div>
    </section>

    <SaveDatasetDialog
      v-if="canCreate"
      :open="saveDialogOpen"
      :datasource-id="datasource.id"
      :sql="sql"
      :parameters="parameters"
      @close="saveDialogOpen = false"
    />
  </div>
</template>
