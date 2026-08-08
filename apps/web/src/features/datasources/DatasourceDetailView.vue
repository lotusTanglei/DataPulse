<script setup lang="ts">
import { Pencil } from "@lucide/vue";
import {
  computed,
  defineAsyncComponent,
  onBeforeUnmount,
  ref,
  watch,
} from "vue";
import { RouterLink, useRoute } from "vue-router";

import { ApiError } from "../../lib/api";
import InlineNotice from "../../ui/InlineNotice.vue";
import { getDatasource } from "./api";
import SchemaBrowser from "./SchemaBrowser.vue";
import type {
  ConnectorType,
  Datasource,
  DatasourceConfig,
  DatasourceStatus,
} from "./types";

type DetailTab = "overview" | "schema" | "sql" | "settings";

const route = useRoute();
const SqlDebugView = defineAsyncComponent(
  () => import("../query/SqlDebugView.vue"),
);
const datasource = ref<Datasource | null>(null);
const loading = ref(true);
const error = ref<ApiError | null>(null);
const activeTab = ref<DetailTab>("overview");
let loadController: AbortController | null = null;

const tabs = computed(() =>
  datasource.value?.config.type === "http_api"
    ? [{ id: "overview", label: "概览" }, { id: "settings", label: "设置" }]
    : [
        { id: "overview", label: "概览" },
        { id: "schema", label: "Schema" },
        { id: "sql", label: "SQL 调试" },
        { id: "settings", label: "设置" },
      ],
);

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

const address = computed(() => {
  const config = datasource.value?.config;
  if (config === undefined) {
    return "";
  }
  return safeAddress(config);
});

function safeAddress(config: DatasourceConfig): string {
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
    return "尚未检查";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

async function load(id: string): Promise<void> {
  loadController?.abort();
  const controller = new AbortController();
  loadController = controller;
  loading.value = true;
  error.value = null;
  datasource.value = null;
  try {
    const loaded = await getDatasource(id, controller.signal);
    if (!controller.signal.aborted) {
      datasource.value = loaded;
    }
  } catch (reason) {
    if (!controller.signal.aborted) {
      error.value =
        reason instanceof ApiError
          ? reason
          : new ApiError({
              code: "DATASOURCE_LOAD_FAILED",
              message: "暂时无法加载数据源。",
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

watch(
  () => String(route.params.id ?? ""),
  (id) => {
    activeTab.value = "overview";
    void load(id);
  },
  { immediate: true },
);

onBeforeUnmount(() => loadController?.abort());
</script>

<template>
  <section class="page-column datasource-detail-page" aria-labelledby="datasource-detail-title">
    <p v-if="loading" class="loading-copy" role="status">正在加载数据源…</p>

    <InlineNotice v-else-if="error" tone="error">
      <p>{{ error.message }}</p>
      <code v-if="error.requestId">{{ error.requestId }}</code>
    </InlineNotice>

    <template v-else-if="datasource">
      <div class="detail-heading">
        <div class="detail-title">
          <span class="datasource-monogram datasource-monogram--large" aria-hidden="true">
            {{ datasource.name.slice(0, 1).toUpperCase() }}
          </span>
          <div>
            <p class="page-eyebrow">{{ typeLabels[datasource.config.type] }}</p>
            <h1 id="datasource-detail-title">{{ datasource.name }}</h1>
            <p class="page-description">{{ address }}</p>
          </div>
        </div>
        <RouterLink
          class="secondary-button"
          :to="`/studio/datasources/${datasource.id}/edit`"
        >
          <Pencil :size="14" aria-hidden="true" />
          编辑连接
        </RouterLink>
      </div>

      <div class="detail-tabs" role="tablist" aria-label="数据源详情">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          role="tab"
          type="button"
          :data-tab="tab.id"
          :aria-selected="activeTab === tab.id"
          @click="activeTab = tab.id as DetailTab"
        >
          {{ tab.label }}
        </button>
      </div>

      <div v-if="activeTab === 'overview'" class="detail-panel">
        <dl class="property-grid">
          <div>
            <dt>连接器</dt>
            <dd>{{ typeLabels[datasource.config.type] }}</dd>
          </div>
          <div>
            <dt>地址</dt>
            <dd><code>{{ address }}</code></dd>
          </div>
          <div>
            <dt>连接状态</dt>
            <dd>
              <span class="status-copy" :data-status="datasource.status">
                <span class="status-dot" aria-hidden="true" />
                {{ statusLabels[datasource.status] }}
              </span>
            </dd>
          </div>
          <div>
            <dt>上次检查</dt>
            <dd>{{ formattedDate(datasource.last_checked_at) }}</dd>
          </div>
          <div>
            <dt>响应延迟</dt>
            <dd>
              {{ datasource.last_latency_ms === null ? "—" : `${datasource.last_latency_ms} ms` }}
            </dd>
          </div>
          <div>
            <dt>凭据</dt>
            <dd>{{ datasource.has_password ? "已保存" : "未保存密码" }}</dd>
          </div>
        </dl>
      </div>

      <div v-else-if="activeTab === 'schema'" class="detail-panel detail-panel--flush">
        <SchemaBrowser :datasource="datasource" />
      </div>

      <div v-else-if="activeTab === 'sql'" class="detail-panel detail-panel--flush">
        <SqlDebugView :datasource="datasource" />
      </div>

      <div v-else class="detail-panel">
        <h2>连接设置</h2>
        <p class="page-description">更新地址、账号、SSL 模式或密码。</p>
        <RouterLink
          class="secondary-button"
          :to="`/studio/datasources/${datasource.id}/edit`"
        >
          <Pencil :size="14" aria-hidden="true" />
          编辑连接配置
        </RouterLink>
      </div>
    </template>
  </section>
</template>
