<script setup lang="ts">
import { X } from "@lucide/vue";
import { ref, watch } from "vue";
import { useRouter } from "vue-router";

import { ApiError } from "../../lib/api";
import InlineNotice from "../../ui/InlineNotice.vue";
import type { QueryParameterInput } from "../query/types";
import { createDataset } from "./api";

const props = defineProps<{
  open: boolean;
  datasourceId: string;
  sql: string;
  parameters: QueryParameterInput[];
}>();

const emit = defineEmits<{ close: [] }>();
const router = useRouter();
const name = ref("");
const submitting = ref(false);
const nameError = ref("");
const error = ref<ApiError | null>(null);

watch(
  () => props.open,
  (open) => {
    if (open) {
      name.value = "";
      nameError.value = "";
      error.value = null;
    }
  },
);

async function submit(): Promise<void> {
  nameError.value = "";
  error.value = null;
  if (name.value.trim() === "") {
    nameError.value = "请输入数据集名称";
    return;
  }
  submitting.value = true;
  try {
    const created = await createDataset({
      name: name.value.trim(),
      data_source_id: props.datasourceId,
      sql: props.sql,
      parameters: props.parameters.map((parameter) => ({
        name: parameter.name.trim(),
        data_type: parameter.data_type,
        required: false,
        default: parameter.value,
      })),
      max_rows: 5000,
      timeout_seconds: 30,
    });
    emit("close");
    await router.push(`/studio/datasets/${created.id}`);
  } catch (reason) {
    error.value =
      reason instanceof ApiError
        ? reason
        : new ApiError({
            code: "DATASET_CREATE_FAILED",
            message: "暂时无法保存数据集。",
            requestId: "",
            status: 500,
          });
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div v-if="open" class="dialog-backdrop" @click.self="emit('close')">
    <section
      class="dialog-card save-dataset-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="save-dataset-title"
    >
      <div class="dialog-heading">
        <div>
          <p class="page-eyebrow">保存查询</p>
          <h2 id="save-dataset-title">保存为数据集</h2>
        </div>
        <button
          class="icon-button"
          type="button"
          aria-label="关闭"
          @click="emit('close')"
        >
          <X :size="16" aria-hidden="true" />
        </button>
      </div>

      <form class="dialog-form" @submit.prevent="submit">
        <label>
          <span>数据集名称</span>
          <input
            v-model="name"
            name="datasetName"
            autocomplete="off"
            placeholder="例如：月度销售"
          />
          <small v-if="nameError" class="field-error">{{ nameError }}</small>
        </label>
        <label>
          <span>SQL</span>
          <textarea
            name="datasetSql"
            :value="sql"
            rows="6"
            readonly
          />
        </label>
        <div class="dialog-summary">
          <span>数据源 {{ datasourceId }}</span>
          <span>{{ parameters.length }} 个参数</span>
          <span>最多 5,000 行</span>
        </div>

        <InlineNotice v-if="error" tone="error">
          <p>{{ error.message }}</p>
          <code v-if="error.requestId">{{ error.requestId }}</code>
        </InlineNotice>

        <div class="dialog-actions">
          <button
            class="secondary-button"
            type="button"
            @click="emit('close')"
          >
            取消
          </button>
          <button
            class="primary-button"
            type="submit"
            :disabled="submitting"
          >
            {{ submitting ? "正在保存…" : "保存数据集" }}
          </button>
        </div>
      </form>
    </section>
  </div>
</template>
