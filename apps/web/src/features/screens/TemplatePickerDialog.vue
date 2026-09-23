<script setup lang="ts">
import { Check, LayoutTemplate, X } from "@lucide/vue";
import { computed, onMounted, ref, watch } from "vue";

import type { DashboardDocument } from "../../contracts";
import { listDatasets } from "../datasets/api";
import type { Dataset } from "../datasets/types";
import type { QueryResult } from "../query/types";
import ScreenRuntime from "../runtime/ScreenRuntime.vue";
import type { QueryComponent } from "../runtime/types";
import { createTemplateDocument, screenTemplates, type ScreenTemplate } from "./templates";

const props = withDefaults(
  defineProps<{
    open: boolean;
    submitting?: boolean;
  }>(),
  { submitting: false },
);

const emit = defineEmits<{
  close: [];
  confirm: [payload: { name: string; template: ScreenTemplate; dataset: Dataset }];
}>();

const selectedId = ref(screenTemplates[0]?.id ?? "");
const selectedDatasetId = ref("");
const datasets = ref<Dataset[]>([]);
const loadingDatasets = ref(false);
const name = ref("");
const error = ref("");
const selected = computed(() =>
  screenTemplates.find((template) => template.id === selectedId.value) ??
  screenTemplates[0],
);
const previewDocument = computed<DashboardDocument | null>(() =>
  selected.value ? createTemplateDocument(selected.value.id) : null,
);
const previewQuery: QueryComponent = async (): Promise<QueryResult> => ({
  request_id: "template-preview",
  columns: [],
  rows: [],
  row_count: 0,
  truncated: false,
  duration_ms: 0,
});
const previewAsset = async (): Promise<string> => "";
const canRenderRuntimePreview = ref(false);

onMounted(() => {
  try {
    const canvas = document.createElement("canvas");
    canRenderRuntimePreview.value = Boolean(canvas.getContext("2d"));
  } catch {
    canRenderRuntimePreview.value = false;
  }
});

watch(
  () => props.open,
  (open) => {
    if (open) {
      selectedId.value = screenTemplates[0]?.id ?? "";
      selectedDatasetId.value = "";
      name.value = "";
      error.value = "";
      loadingDatasets.value = true;
      void listDatasets()
        .then((items) => {
          datasets.value = items;
        })
        .catch(() => {
          datasets.value = [];
          error.value = "暂时无法加载数据集。";
        })
        .finally(() => {
          loadingDatasets.value = false;
        });
    }
  },
);

function submit(): void {
  const template = selected.value;
  const dataset = datasets.value.find(
    (item) => item.id === selectedDatasetId.value,
  );
  const nextName = name.value.trim();
  if (!template) {
    error.value = "请选择一个模板。";
    return;
  }
  if (!nextName) {
    error.value = "请输入大屏名称。";
    return;
  }
  if (!dataset) {
    error.value = "请选择一个包含字段的数据集。";
    return;
  }
  emit("confirm", { name: nextName, template, dataset });
}
</script>

<template>
  <div
    v-if="open"
    class="dialog-backdrop"
    role="presentation"
    @mousedown.self="!submitting && emit('close')"
  >
    <section
      class="dialog-card template-picker-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="template-picker-title"
    >
      <div class="dialog-heading">
        <div>
          <h2 id="template-picker-title">从模板创建</h2>
          <p>选择后仍会进入同一个编辑器，可继续绑定数据和调整布局。</p>
        </div>
        <button
          class="dialog-close"
          type="button"
          aria-label="关闭模板选择"
          :disabled="submitting"
          @click="emit('close')"
        >
          <X :size="16" aria-hidden="true" />
        </button>
      </div>

      <label class="form-field">
        <span class="form-field__heading">大屏名称</span>
        <input
          v-model="name"
          name="templateScreenName"
          autocomplete="off"
          autofocus
          placeholder="例如：华东区域经营分析"
          @input="error = ''"
        />
      </label>

      <label class="form-field">
        <span class="form-field__heading">数据集</span>
        <select
          v-model="selectedDatasetId"
          name="templateDataset"
          :disabled="loadingDatasets || submitting"
          @change="error = ''"
        >
          <option value="">
            {{ loadingDatasets ? "正在加载数据集…" : "请选择数据集" }}
          </option>
          <option
            v-for="dataset in datasets"
            :key="dataset.id"
            :value="dataset.id"
            :disabled="(dataset.definition?.fields?.length ?? 0) === 0"
          >
            {{ dataset.name }} · {{ dataset.id }}
          </option>
        </select>
      </label>

      <div class="template-picker__content">
        <div class="template-picker__list" aria-label="大屏模板">
          <button
            v-for="template in screenTemplates"
            :key="template.id"
            class="template-option"
            :class="{ 'is-selected': selectedId === template.id }"
            type="button"
            :aria-pressed="selectedId === template.id"
            @click="selectedId = template.id"
          >
            <span class="template-option__icon" aria-hidden="true">
              <Check v-if="selectedId === template.id" :size="16" />
              <LayoutTemplate v-else :size="16" />
            </span>
            <span>
              <strong>{{ template.name }}</strong>
              <small>{{ template.category }}</small>
            </span>
          </button>
        </div>
        <div v-if="selected" class="template-picker__preview">
          <div class="template-picker__preview-canvas">
            <ScreenRuntime
              v-if="previewDocument && canRenderRuntimePreview"
              :document="previewDocument"
              mode="preview"
              :load-asset="previewAsset"
              :query-component="previewQuery"
            />
            <div v-else class="template-picker__fallback-preview" aria-hidden="true">
              <i class="template-picker__fallback-title"></i>
              <div class="template-picker__fallback-metrics">
                <i v-for="index in 4" :key="index"></i>
              </div>
              <div class="template-picker__fallback-charts">
                <i></i><i></i><i></i>
              </div>
            </div>
          </div>
          <div class="template-picker__preview-copy">
            <p class="page-eyebrow">{{ selected.category }}</p>
            <h3>{{ selected.name }}</h3>
            <p>{{ selected.description }}</p>
            <span>1920 × 1080 · 含演示数据</span>
          </div>
        </div>
      </div>

      <p v-if="error" class="form-field__error">{{ error }}</p>
      <div class="dialog-actions">
        <button
          class="secondary-button"
          type="button"
          :disabled="submitting"
          @click="emit('close')"
        >
          取消
        </button>
        <button
          class="primary-button"
          type="button"
          :disabled="submitting"
          @click="submit"
        >
          {{ submitting ? "正在创建…" : "使用此模板" }}
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.template-picker-dialog {
  width: min(760px, calc(100vw - 32px));
}

.template-picker__content {
  display: grid;
  grid-template-columns: minmax(220px, 0.9fr) minmax(0, 1.1fr);
  gap: 12px;
  margin-top: 16px;
}

.template-picker__list {
  display: grid;
  gap: 8px;
}

.template-option {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 58px;
  padding: 10px 12px;
  border: 1px solid rgb(148 163 184 / 22%);
  border-radius: 8px;
  background: rgb(15 23 42 / 34%);
  color: inherit;
  text-align: left;
}

.template-option:hover,
.template-option.is-selected {
  border-color: rgb(96 165 250 / 70%);
  background: rgb(30 64 175 / 18%);
}

.template-option__icon {
  display: grid;
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  place-items: center;
  border-radius: 6px;
  background: rgb(59 130 246 / 16%);
  color: #93c5fd;
}

.template-option strong,
.template-option small {
  display: block;
}

.template-option small {
  margin-top: 3px;
  color: #94a3b8;
  font-size: 12px;
}

.template-picker__preview {
  display: grid;
  gap: 12px;
  min-height: 230px;
  border: 1px solid rgb(148 163 184 / 20%);
  border-radius: 8px;
  background: #0f172a;
}

.template-picker__preview-canvas {
  position: relative;
  height: 230px;
  overflow: hidden;
  border-bottom: 1px solid rgb(148 163 184 / 16%);
}

.template-picker__fallback-preview {
  display: grid;
  gap: 8px;
  height: 100%;
  padding: 16px;
  background:
    linear-gradient(rgb(34 211 238 / 7%) 1px, transparent 1px),
    linear-gradient(90deg, rgb(34 211 238 / 7%) 1px, transparent 1px),
    #071522;
  background-size: 16px 16px;
}

.template-picker__fallback-preview i {
  display: block;
  border: 1px solid rgb(45 212 191 / 32%);
  background: rgb(15 57 77 / 72%);
}

.template-picker__fallback-title {
  width: 42%;
  height: 10px;
  border: 0 !important;
  background: rgb(226 232 240 / 72%) !important;
}

.template-picker__fallback-metrics,
.template-picker__fallback-charts {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 7px;
}

.template-picker__fallback-metrics {
  height: 46px;
}

.template-picker__fallback-charts {
  grid-template-columns: 1.2fr 0.8fr 1fr;
  height: 120px;
}

.template-picker__preview-copy {
  display: grid;
  gap: 6px;
  padding: 0 16px 16px;
}

.template-picker__preview-copy h3 {
  margin: 0;
  font-size: 24px;
}

.template-picker__preview-copy p:not(.page-eyebrow) {
  margin: 0;
  color: #b4c2d6;
  line-height: 1.6;
}

.template-picker__preview span {
  color: #64748b;
  font-size: 12px;
}

@media (max-width: 640px) {
  .template-picker__content {
    grid-template-columns: 1fr;
  }
}
</style>
