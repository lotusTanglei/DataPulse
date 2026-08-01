<script setup lang="ts">
import { FileUp, Trash2 } from "@lucide/vue";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { ApiError } from "../../lib/api";
import InlineNotice from "../../ui/InlineNotice.vue";
import {
  deleteFileAsset,
  listFileAssets,
  previewFileAsset,
  uploadFileAsset,
} from "../files/api";
import type { FileAsset, FilePreviewResponse } from "../files/types";
import QueryResultTable from "../query/QueryResultTable.vue";
import { createFileDataset } from "./api";

const router = useRouter();
const loading = ref(true);
const uploading = ref(false);
const previewing = ref(false);
const deleting = ref(false);
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
const previewError = ref<ApiError | null>(null);
const previewResponse = ref<FilePreviewResponse | null>(null);
let previewController: AbortController | null = null;

const selectedAsset = computed(() =>
  assets.value.find((asset) => asset.id === selectedAssetId.value) ?? null,
);
const needsSheetName = computed(() => selectedAsset.value?.format === "excel");
const sheetNames = computed(() => previewResponse.value?.sheet_names ?? []);
const canSubmit = computed(
  () =>
    selectedAsset.value !== null &&
    name.value.trim() !== "" &&
    !uploading.value &&
    !submitting.value &&
    (!needsSheetName.value || sheetName.value.trim() !== ""),
);

function fallbackError(reason: unknown, code: string, message: string): ApiError {
  return reason instanceof ApiError
    ? reason
    : new ApiError({ code, message, requestId: "", status: 500 });
}

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

async function loadPreview(
  assetId: string,
  requestedSheet?: string,
): Promise<void> {
  previewController?.abort();
  previewResponse.value = null;
  previewError.value = null;
  if (!assetId) {
    previewing.value = false;
    return;
  }
  const controller = new AbortController();
  previewController = controller;
  previewing.value = true;
  try {
    const response = await previewFileAsset(
      assetId,
      requestedSheet,
      controller.signal,
    );
    if (!controller.signal.aborted) {
      previewResponse.value = response;
      sheetName.value = response.selected_sheet ?? "";
    }
  } catch (reason) {
    if (!controller.signal.aborted) {
      previewError.value = fallbackError(
        reason,
        "FILE_PREVIEW_FAILED",
        "文件样例预览失败，请稍后重试。",
      );
    }
  } finally {
    if (!controller.signal.aborted) {
      previewing.value = false;
    }
  }
}

function onSheetChange(): void {
  if (selectedAssetId.value && sheetName.value) {
    void loadPreview(selectedAssetId.value, sheetName.value);
  }
}

async function removeSelectedAsset(): Promise<void> {
  const asset = selectedAsset.value;
  if (
    asset === null ||
    deleting.value ||
    !window.confirm(
      `删除文件“${asset.original_name}”？仅未被数据集引用的文件可以删除。`,
    )
  ) {
    return;
  }
  deleting.value = true;
  uploadError.value = null;
  try {
    await deleteFileAsset(asset.id);
    assets.value = assets.value.filter((item) => item.id !== asset.id);
    selectedAssetId.value = assets.value[0]?.id ?? "";
  } catch (reason) {
    uploadError.value = fallbackError(
      reason,
      "FILE_DELETE_FAILED",
      "文件删除失败；请确认它没有被数据集引用。",
    );
  } finally {
    deleting.value = false;
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

watch(selectedAssetId, (assetId) => {
  sheetName.value = "";
  void loadPreview(assetId);
});

onMounted(() => void load());
onBeforeUnmount(() => previewController?.abort());
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
              <div class="query-actions">
                <span class="type-pill">{{ formatLabel(selectedAsset.format) }}</span>
                <button
                  class="secondary-button primary-button--compact"
                  type="button"
                  data-action="delete-file-asset"
                  :disabled="deleting"
                  @click="removeSelectedAsset"
                >
                  <Trash2 :size="13" aria-hidden="true" />
                  {{ deleting ? "正在删除…" : "删除文件" }}
                </button>
              </div>
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
              <span>Excel Sheet</span>
              <select
                v-model="sheetName"
                name="sheetName"
                :disabled="previewing || sheetNames.length === 0"
                @change="onSheetChange"
              >
                <option v-for="sheet in sheetNames" :key="sheet" :value="sheet">
                  {{ sheet }}
                </option>
              </select>
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
          <InlineNotice v-if="previewError" tone="error">
            <p>{{ previewError.message }}</p>
            <code v-if="previewError.requestId">{{ previewError.requestId }}</code>
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

      <div v-if="previewResponse" class="query-result-panel">
        <div class="result-summary">
          <strong>{{ previewResponse.result.row_count.toLocaleString("zh-CN") }} 行样例</strong>
          <span>{{ previewResponse.result.duration_ms.toLocaleString("zh-CN") }} ms</span>
          <code>{{ previewResponse.result.request_id }}</code>
        </div>
        <QueryResultTable :result="previewResponse.result" />
      </div>
      <p v-else-if="previewing" class="loading-copy" role="status">
        正在加载文件样例…
      </p>
    </template>
  </section>
</template>
