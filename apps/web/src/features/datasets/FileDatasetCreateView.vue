<script setup lang="ts">
import { FileUp } from "@lucide/vue";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { ApiError } from "../../lib/api";
import InlineNotice from "../../ui/InlineNotice.vue";
import { listFileAssets, uploadFileAsset } from "../files/api";
import type { FileAsset } from "../files/types";
import { createFileDataset } from "./api";

const router = useRouter();
const loading = ref(true);
const uploading = ref(false);
const submitting = ref(false);
const assets = ref<FileAsset[]>([]);
const selectedAssetId = ref("");
const name = ref("");
const sheetName = ref("");
const maxRows = ref(5000);
const timeoutSeconds = ref(30);
const loadError = ref<ApiError | null>(null);
const uploadError = ref<ApiError | null>(null);
const submitError = ref<ApiError | null>(null);

const selectedAsset = computed(() =>
  assets.value.find((asset) => asset.id === selectedAssetId.value) ?? null,
);
const needsSheetName = computed(() => selectedAsset.value?.format === "excel");
const canSubmit = computed(
  () =>
    selectedAsset.value !== null &&
    name.value.trim() !== "" &&
    !uploading.value &&
    !submitting.value,
);

async function load(): Promise<void> {
  loading.value = true;
  loadError.value = null;
  try {
    assets.value = await listFileAssets();
    selectedAssetId.value = assets.value[0]?.id ?? "";
  } catch (reason) {
    loadError.value =
      reason instanceof ApiError
        ? reason
        : new ApiError({
            code: "FILE_LIST_FAILED",
            message: "暂时无法加载文件资产。",
            requestId: "",
            status: 500,
          });
  } finally {
    loading.value = false;
  }
}

function suggestName(fileName: string): void {
  if (name.value.trim() !== "") {
    return;
  }
  name.value = fileName.replace(/\.[^.]+$/, "");
}

async function onFileChange(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) {
    return;
  }
  uploading.value = true;
  uploadError.value = null;
  try {
    const asset = await uploadFileAsset(file);
    assets.value = [asset, ...assets.value.filter((item) => item.id !== asset.id)];
    selectedAssetId.value = asset.id;
    suggestName(asset.original_name);
  } catch (reason) {
    uploadError.value =
      reason instanceof ApiError
        ? reason
        : new ApiError({
            code: "FILE_UPLOAD_FAILED",
            message: "文件上传失败，请稍后重试。",
            requestId: "",
            status: 500,
          });
  } finally {
    uploading.value = false;
    input.value = "";
  }
}

async function submit(): Promise<void> {
  if (!canSubmit.value || selectedAsset.value === null) {
    return;
  }
  submitting.value = true;
  submitError.value = null;
  try {
    const nextSheetName = needsSheetName.value && sheetName.value.trim() !== ""
      ? sheetName.value.trim()
      : null;
    const created = await createFileDataset({
      name: name.value.trim(),
      file_asset_id: selectedAsset.value.id,
      max_rows: maxRows.value,
      timeout_seconds: timeoutSeconds.value,
      ...(nextSheetName === null ? {} : { sheet_name: nextSheetName }),
    });
    await router.push(`/studio/datasets/${created.id}`);
  } catch (reason) {
    submitError.value =
      reason instanceof ApiError
        ? reason
        : new ApiError({
            code: "FILE_DATASET_CREATE_FAILED",
            message: "暂时无法创建文件数据集。",
            requestId: "",
            status: 500,
          });
  } finally {
    submitting.value = false;
  }
}

function formatLabel(value: string): string {
  return value.toUpperCase();
}

onMounted(() => void load());
</script>

<template>
  <section class="page-column dataset-file-page" aria-labelledby="dataset-file-title">
    <div class="page-heading">
      <div>
        <p class="page-eyebrow">文件工作台</p>
        <h1 id="dataset-file-title">导入文件数据集</h1>
        <p class="page-description">
          上传 CSV、Excel、JSON 或 Parquet 文件，生成可预览的只读数据集。
        </p>
      </div>
    </div>

    <p v-if="loading" class="loading-copy" role="status">正在加载文件资产…</p>
    <InlineNotice v-else-if="loadError" tone="error">
      <p>{{ loadError.message }}</p>
      <code v-if="loadError.requestId">{{ loadError.requestId }}</code>
    </InlineNotice>

    <template v-else>
      <div class="dataset-file-layout">
        <section class="dataset-file-panel">
          <div class="dataset-file-uploader">
            <div>
              <h2>上传文件</h2>
              <p>选择一个文件后会立即上传并解析字段。</p>
            </div>
            <label class="secondary-button dataset-file-input">
              <FileUp :size="14" aria-hidden="true" />
              {{ uploading ? "正在上传…" : "选择文件" }}
              <input
                name="fileAsset"
                type="file"
                :disabled="uploading"
                @change="onFileChange"
              />
            </label>
          </div>

          <InlineNotice v-if="uploadError" tone="error">
            <p>{{ uploadError.message }}</p>
            <code v-if="uploadError.requestId">{{ uploadError.requestId }}</code>
          </InlineNotice>

          <label>
            <span>已上传文件</span>
            <select v-model="selectedAssetId" name="selectedAsset">
              <option value="">请选择文件</option>
              <option v-for="asset in assets" :key="asset.id" :value="asset.id">
                {{ asset.original_name }}
              </option>
            </select>
          </label>

          <div v-if="selectedAsset" class="dataset-file-asset">
            <div class="dataset-file-asset__header">
              <strong>{{ selectedAsset.original_name }}</strong>
              <span class="type-pill">{{ formatLabel(selectedAsset.format) }}</span>
            </div>
            <p>
              {{ selectedAsset.row_count.toLocaleString("zh-CN") }} 行 ·
              {{ selectedAsset.fields.length }} 个字段
            </p>
            <ul class="dataset-file-fields">
              <li v-for="field in selectedAsset.fields" :key="field.name">
                <code>{{ field.name }}</code>
                <span>{{ field.data_type }}</span>
              </li>
            </ul>
          </div>
        </section>

        <section class="dataset-file-panel">
          <h2>数据集配置</h2>
          <div class="dataset-config-grid dataset-config-grid--stacked">
            <label>
              <span>数据集名称</span>
              <input
                v-model="name"
                name="datasetName"
                autocomplete="off"
                placeholder="例如：销售文件数据集"
              />
            </label>
            <label v-if="needsSheetName">
              <span>Excel Sheet（可选）</span>
              <input
                v-model="sheetName"
                name="sheetName"
                autocomplete="off"
                placeholder="例如：Sheet1"
              />
            </label>
            <label>
              <span>最大行数</span>
              <input
                v-model.number="maxRows"
                name="maxRows"
                type="number"
                min="1"
                max="5000"
              />
            </label>
            <label>
              <span>超时（秒）</span>
              <input
                v-model.number="timeoutSeconds"
                name="timeoutSeconds"
                type="number"
                min="1"
                max="300"
              />
            </label>
          </div>

          <InlineNotice v-if="submitError" tone="error">
            <p>{{ submitError.message }}</p>
            <code v-if="submitError.requestId">{{ submitError.requestId }}</code>
          </InlineNotice>

          <div class="dialog-actions">
            <button
              class="primary-button"
              data-action="create-file-dataset"
              type="button"
              :disabled="!canSubmit"
              @click="submit"
            >
              {{ submitting ? "正在创建…" : "创建数据集" }}
            </button>
          </div>
        </section>
      </div>
    </template>
  </section>
</template>
