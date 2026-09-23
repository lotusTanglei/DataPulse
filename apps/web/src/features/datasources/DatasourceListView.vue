<script setup lang="ts">
import { PlugZap, Plus } from "@lucide/vue";
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import { ApiError } from "../../lib/api";
import InlineNotice from "../../ui/InlineNotice.vue";
import { useStudioPermissions } from "../identity/permissions";
import { listDatasources, testDatasource } from "./api";
import type {
  ConnectorType,
  Datasource,
  DatasourceConfig,
  DatasourceStatus,
} from "./types";

const datasources = ref<Datasource[]>([]);
const { isAdmin, canCreate, canWriteResource } = useStudioPermissions();
const writable = ref<Record<string, boolean>>({});
const canWrite = (id: string) => isAdmin.value || writable.value[id] === true;
const loading = ref(true);
const error = ref<ApiError | null>(null);
const testingIds = ref<Set<string>>(new Set());
const rowErrors = ref<Record<string, string>>({});
const copiedRequestId = ref(false);

const typeLabels: Record<ConnectorType, string> = {
  sqlite: "SQLite",
  postgresql: "PostgreSQL",
  mysql: "MySQL / MariaDB",
  http_api: "HTTP API",
};

const statusLabels: Record<DatasourceStatus, string> = {
  available: "可用",
  unavailable: "不可用",
  unknown: "未检查",
};

const statusAriaLabels: Record<DatasourceStatus, string> = {
  available: "连接可用",
  unavailable: "连接不可用",
  unknown: "连接尚未检查",
};

function address(config: DatasourceConfig): string {
  if (config.type === "sqlite") {
    return config.path;
  }
  if (config.type === "http_api") {
    return config.base_url;
  }
  return `${config.host}:${config.port}/${config.database}`;
}

function formattedDate(value: string | null): string {
  if (value === null) {
    return "—";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

async function load(): Promise<void> {
  loading.value = true;
  error.value = null;
  try {
    datasources.value = await listDatasources();
    writable.value = Object.fromEntries(await Promise.all(datasources.value.map(async (source) => [
      source.id, await canWriteResource("datasource", source.id),
    ])));
  } catch (reason) {
    error.value =
      reason instanceof ApiError
        ? reason
        : new ApiError({
            code: "DATASOURCE_LIST_FAILED",
            message: "暂时无法加载数据源。",
            requestId: "",
            status: 500,
          });
  } finally {
    loading.value = false;
  }
}

async function testConnection(datasource: Datasource): Promise<void> {
  if (!canWrite(datasource.id) || testingIds.value.has(datasource.id)) {
    return;
  }
  testingIds.value = new Set(testingIds.value).add(datasource.id);
  const nextErrors = { ...rowErrors.value };
  delete nextErrors[datasource.id];
  rowErrors.value = nextErrors;
  try {
    const updated = await testDatasource(datasource.id);
    datasources.value = datasources.value.map((item) =>
      item.id === updated.id ? updated : item,
    );
  } catch (reason) {
    rowErrors.value = {
      ...rowErrors.value,
      [datasource.id]:
        reason instanceof ApiError ? reason.message : "连接测试失败，请稍后重试。",
    };
  } finally {
    const next = new Set(testingIds.value);
    next.delete(datasource.id);
    testingIds.value = next;
  }
}

async function copyRequestId(): Promise<void> {
  if (!error.value?.requestId) {
    return;
  }
  try {
    await navigator.clipboard.writeText(error.value.requestId);
    copiedRequestId.value = true;
  } catch {
    copiedRequestId.value = false;
  }
}

onMounted(load);
</script>

<template>
  <section class="page-column datasource-page" aria-labelledby="datasource-title">
    <div class="page-heading-row">
      <div>
        <p class="page-eyebrow">Workspace</p>
        <h1 id="datasource-title">数据源</h1>
        <p class="page-description">连接并管理用于分析的数据库。</p>
      </div>
      <RouterLink
        v-if="canCreate && datasources.length > 0"
        class="primary-button primary-button--compact"
        to="/studio/datasources/new"
      >
        <Plus :size="14" aria-hidden="true" />
        新建数据源
      </RouterLink>
    </div>

    <p v-if="loading" class="loading-copy" role="status">正在加载数据源…</p>

    <InlineNotice v-else-if="error" tone="error">
      <p>{{ error.message }}</p>
      <div v-if="error.requestId" class="request-id-row">
        <code>{{ error.requestId }}</code>
        <button
          class="text-button"
          type="button"
          aria-label="复制请求 ID"
          @click="copyRequestId"
        >
          {{ copiedRequestId ? "已复制" : "复制" }}
        </button>
      </div>
    </InlineNotice>

    <div v-else-if="datasources.length === 0" class="empty-panel datasource-empty">
      <RouterLink
        v-if="canCreate"
        class="empty-panel__icon"
        to="/studio/datasources/new"
        aria-label="新建数据源"
      >
        <Plus :size="20" aria-hidden="true" />
      </RouterLink>
      <h2>还没有数据源</h2>
      <p>{{ canCreate ? "添加数据库或 HTTP API 连接。" : "请联系资源拥有者共享数据源。" }}</p>
    </div>

    <div v-else class="notion-table-wrap">
      <table class="notion-table">
        <thead>
          <tr>
            <th>名称</th>
            <th>类型</th>
            <th>地址</th>
            <th>状态</th>
            <th>上次检查</th>
            <th>上次查询</th>
            <th class="notion-table__actions">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="datasource in datasources"
            :key="datasource.id"
            :data-source-id="datasource.id"
          >
            <td>
              <RouterLink
                class="datasource-name"
                :to="`/studio/datasources/${datasource.id}`"
              >
                <span class="datasource-monogram" aria-hidden="true">
                  {{ datasource.name.slice(0, 1).toUpperCase() }}
                </span>
                <span>{{ datasource.name }}</span>
              </RouterLink>
            </td>
            <td>
              <span class="type-pill">{{ typeLabels[datasource.config.type] }}</span>
            </td>
            <td><code class="address-copy">{{ address(datasource.config) }}</code></td>
            <td>
              <span class="status-copy" :data-status="datasource.status">
                <span
                  class="status-dot"
                  role="img"
                  :aria-label="statusAriaLabels[datasource.status]"
                />
                {{ statusLabels[datasource.status] }}
              </span>
            </td>
            <td>{{ formattedDate(datasource.last_checked_at) }}</td>
            <td>—</td>
            <td class="notion-table__actions">
              <button
                v-if="canWrite(datasource.id)"
                class="table-action"
                type="button"
                :aria-label="`测试连接：${datasource.name}`"
                :disabled="testingIds.has(datasource.id)"
                @click="testConnection(datasource)"
              >
                <PlugZap v-if="!testingIds.has(datasource.id)" :size="13" aria-hidden="true" />
                {{ testingIds.has(datasource.id) ? "测试中…" : "测试" }}
              </button>
              <p v-if="rowErrors[datasource.id]" class="table-row-error">
                {{ rowErrors[datasource.id] }}
              </p>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
