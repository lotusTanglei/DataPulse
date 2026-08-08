<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { ApiError } from "../../lib/api";
import InlineNotice from "../../ui/InlineNotice.vue";
import { listDatasources } from "../datasources/api";
import type { Datasource } from "../datasources/types";
import { createDataset } from "./api";
import type { JsonValue } from "../query/types";

const router = useRouter();
const sources = ref<Datasource[]>([]);
const loading = ref(true);
const submitting = ref(false);
const notice = ref("");
const sourceId = ref("");
const name = ref("");
const method = ref<"GET" | "POST">("GET");
const url = ref("");
const queryText = ref("{}");
const bodyText = ref("{}");
const responsePath = ref("");
const fieldError = ref("");

const httpSources = computed(() => sources.value.filter((source) => source.config.type === "http_api"));

function parseObject(value: string, label: string): Record<string, JsonValue> | null {
  try {
    const parsed: unknown = JSON.parse(value || "{}");
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
      fieldError.value = `${label}必须是 JSON 对象`;
      return null;
    }
    return parsed as Record<string, JsonValue>;
  } catch {
    fieldError.value = `${label}不是有效的 JSON`;
    return null;
  }
}

async function load(): Promise<void> {
  try {
    sources.value = await listDatasources();
    sourceId.value = httpSources.value[0]?.id ?? "";
    const source = httpSources.value[0];
    if (source?.config.type === "http_api") {
      url.value = source.config.base_url;
    }
  } catch (reason) {
    notice.value = reason instanceof ApiError ? reason.message : "暂时无法加载 HTTP API 数据源。";
  } finally {
    loading.value = false;
  }
}

function selectSource(): void {
  const source = httpSources.value.find((item) => item.id === sourceId.value);
  if (source?.config.type === "http_api" && url.value === "") {
    url.value = source.config.base_url;
  }
}

async function submit(): Promise<void> {
  notice.value = "";
  fieldError.value = "";
  if (!name.value.trim() || !sourceId.value || !url.value.trim()) {
    fieldError.value = "请填写名称、HTTP API 数据源和请求地址";
    return;
  }
  const query = parseObject(queryText.value, "查询参数");
  if (!query) return;
  const body = method.value === "POST" ? parseObject(bodyText.value, "请求体") : null;
  if (method.value === "POST" && !body) return;
  submitting.value = true;
  try {
    const created = await createDataset({
      name: name.value.trim(),
      data_source_id: sourceId.value,
      query: {
        kind: "rest",
        method: method.value,
        url: url.value.trim(),
        query,
        body,
        response_path: responsePath.value.trim() || null,
      },
      parameters: [],
      max_rows: 5000,
      timeout_seconds: 30,
    });
    await router.replace(`/studio/datasets/${created.id}`);
  } catch (reason) {
    notice.value = reason instanceof ApiError ? reason.message : "保存 API 数据集失败。";
  } finally {
    submitting.value = false;
  }
}

onMounted(load);
</script>

<template>
  <section class="page-column dataset-api-create-page" aria-labelledby="api-dataset-title">
    <div class="page-heading-row">
      <div>
        <p class="page-eyebrow">HTTP API</p>
        <h1 id="api-dataset-title">创建 API 数据集</h1>
        <p class="page-description">请求 JSON 接口并映射为可复用的数据集，凭据由数据源统一管理。</p>
      </div>
      <RouterLink class="secondary-button" to="/studio/datasets">返回数据集</RouterLink>
    </div>

    <p v-if="loading" class="loading-copy" role="status">正在加载 HTTP API 数据源…</p>
    <template v-else>
      <InlineNotice v-if="notice" tone="error"><p>{{ notice }}</p></InlineNotice>
      <InlineNotice v-if="httpSources.length === 0" tone="info">
        <p>请先创建一个 HTTP API 数据源。</p>
        <RouterLink to="/studio/datasources/new">创建 HTTP API 数据源</RouterLink>
      </InlineNotice>
      <form v-else class="datasource-form" autocomplete="off" @submit.prevent="submit">
        <div class="form-grid">
          <label class="form-field"><span>数据集名称</span><input v-model="name" autocomplete="off" placeholder="例如：实时订单" /></label>
          <label class="form-field"><span>HTTP API 数据源</span><select v-model="sourceId" @change="selectSource"><option v-for="source in httpSources" :key="source.id" :value="source.id">{{ source.name }}</option></select></label>
          <label class="form-field"><span>请求方法</span><select v-model="method"><option value="GET">GET</option><option value="POST">POST</option></select></label>
          <label class="form-field form-field--wide"><span>请求地址</span><input v-model="url" type="url" autocomplete="off" placeholder="https://api.example.com/v1/orders" /></label>
          <label class="form-field"><span>响应数据路径</span><input v-model="responsePath" autocomplete="off" placeholder="data.items（可选）" /></label>
          <label class="form-field"><span>查询参数 JSON</span><textarea v-model="queryText" rows="5" spellcheck="false" /></label>
          <label v-if="method === 'POST'" class="form-field"><span>请求体 JSON</span><textarea v-model="bodyText" rows="5" spellcheck="false" /></label>
        </div>
        <p v-if="fieldError" class="field-error">{{ fieldError }}</p>
        <div class="form-actions"><RouterLink class="secondary-button" to="/studio/datasets">取消</RouterLink><button class="primary-button" type="submit" :disabled="submitting">{{ submitting ? "正在保存…" : "保存 API 数据集" }}</button></div>
      </form>
    </template>
  </section>
</template>
