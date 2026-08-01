<script setup lang="ts">
import { Braces, Plus } from "@lucide/vue";
import { onBeforeUnmount, ref } from "vue";
import { RouterLink } from "vue-router";

import { ApiError } from "../../lib/api";
import InlineNotice from "../../ui/InlineNotice.vue";
import { listDatasources } from "../datasources/api";
import { listFileAssets } from "../files/api";
import { listDatasets } from "./api";
interface DatasetCardModel {
  id: string;
  name: string;
  sourceLabel: string;
  fieldCount: number;
  parameterCount: number;
}

const datasets = ref<DatasetCardModel[]>([]);
const loading = ref(true);
const error = ref<ApiError | null>(null);
const controller = new AbortController();

async function load(): Promise<void> {
  try {
    const [loadedDatasets, sources, files] = await Promise.all([
      listDatasets(controller.signal),
      listDatasources(controller.signal),
      listFileAssets(controller.signal),
    ]);
    if (!controller.signal.aborted) {
      const sourceNames = new Map(
        sources.map((source) => [source.id, source.name]),
      );
      const fileNames = new Map(
        files.map((asset) => [asset.id, asset.original_name]),
      );
      datasets.value = loadedDatasets.map((dataset) => ({
        id: dataset.id,
        name: dataset.name,
        sourceLabel: dataset.definition.query.kind === "file"
          ? (fileNames.get(dataset.definition.query.asset_id) ?? "上传文件")
          : (sourceNames.get(dataset.data_source_id ?? "") ?? "未知数据源"),
        fieldCount: dataset.definition.fields.length,
        parameterCount: dataset.definition.parameters.length,
      }));
    }
  } catch (reason) {
    if (!controller.signal.aborted) {
      error.value =
        reason instanceof ApiError
          ? reason
          : new ApiError({
              code: "DATASET_LIST_FAILED",
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

void load();
onBeforeUnmount(() => controller.abort());
</script>

<template>
  <section class="page-column dataset-list-page" aria-labelledby="dataset-list-title">
    <div class="page-heading">
      <div>
        <p class="page-eyebrow">可复用查询</p>
        <h1 id="dataset-list-title">数据集</h1>
        <p class="page-description">
          将验证过的只读 SQL、参数和字段定义沉淀为稳定的数据资产。
        </p>
      </div>
      <div class="query-actions">
        <RouterLink class="secondary-button" to="/studio/datasets/files/new">
          <Plus :size="15" aria-hidden="true" />
          导入文件
        </RouterLink>
        <RouterLink class="primary-button" to="/studio/datasources">
          <Plus :size="15" aria-hidden="true" />
          从数据源创建
        </RouterLink>
      </div>
    </div>

    <p v-if="loading" class="loading-copy" role="status">正在加载数据集…</p>
    <InlineNotice v-else-if="error" tone="error">
      <p>{{ error.message }}</p>
      <code v-if="error.requestId">{{ error.requestId }}</code>
    </InlineNotice>

    <div v-else-if="datasets.length === 0" class="empty-state">
      <span class="empty-icon" aria-hidden="true">
        <Braces :size="22" />
      </span>
      <h2>还没有数据集</h2>
      <p>进入一个数据源的 SQL 调试页，运行查询后即可保存。</p>
      <div class="query-actions">
        <RouterLink class="secondary-button" to="/studio/datasets/files/new">
          导入文件
        </RouterLink>
        <RouterLink class="secondary-button" to="/studio/datasources">
          浏览数据源
        </RouterLink>
      </div>
    </div>

    <div v-else class="dataset-grid">
      <RouterLink
        v-for="item in datasets"
        :key="item.id"
        class="dataset-card"
        :to="`/studio/datasets/${item.id}`"
      >
        <span class="dataset-card-icon" aria-hidden="true">
          <Braces :size="17" />
        </span>
        <div>
          <h2>{{ item.name }}</h2>
          <p>{{ item.sourceLabel }}</p>
        </div>
        <div class="dataset-card-meta">
          <span>{{ item.fieldCount }} 个字段</span>
          <span>{{ item.parameterCount }} 个参数</span>
        </div>
      </RouterLink>
    </div>
  </section>
</template>
