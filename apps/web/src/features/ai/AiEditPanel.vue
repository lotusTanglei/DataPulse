<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import { ApiError } from "../../lib/api";
import InlineNotice from "../../ui/InlineNotice.vue";
import { editAi, getAiStatus } from "./api";
import type { AiEditCommand, AiEditResponse } from "./types";
import type { AiHealth } from "./types";
import type { DashboardDocument } from "../../contracts";

const props = defineProps<{
  document: DashboardDocument;
  selectedComponentIds: string[];
  datasetIds: string[];
}>();

const emit = defineEmits<{
  apply: [commands: AiEditCommand[]];
}>();

const question = ref("");
const result = ref<AiEditResponse | null>(null);
const error = ref<ApiError | null>(null);
const formError = ref("");
const generating = ref(false);
const aiStatus = ref<AiHealth | null>(null);

const selectionLabel = computed(() =>
  props.selectedComponentIds.length === 1
    ? "当前选中组件"
    : `当前选中 ${props.selectedComponentIds.length} 个组件`,
);

async function loadAiStatus(): Promise<void> {
  try {
    aiStatus.value = await getAiStatus();
  } catch {
    aiStatus.value = null;
  }
}

watch(
  () => [props.document, props.selectedComponentIds.join(",")],
  () => {
    result.value = null;
    error.value = null;
  },
);

function commandLabel(command: AiEditCommand): string {
  switch (command.type) {
    case "update_frame":
      return "调整布局位置或尺寸";
    case "update_props":
      return "修改组件内容或显示属性";
    case "update_style":
      return "修改组件样式";
    case "update_data_binding":
      return "修改数据绑定和图表配置";
    case "set_component_state":
      return "修改组件状态";
  }
  return "修改组件";
}

async function submit(): Promise<void> {
  const nextQuestion = question.value.trim();
  if (!nextQuestion) {
    formError.value = "请输入希望修改的内容。";
    return;
  }
  if (props.selectedComponentIds.length === 0) {
    formError.value = "请先选择组件。";
    return;
  }
  generating.value = true;
  formError.value = "";
  error.value = null;
  result.value = null;
  try {
    result.value = await editAi({
      question: nextQuestion,
      document: props.document,
      selected_component_ids: props.selectedComponentIds,
      dataset_ids: props.datasetIds,
    });
  } catch (reason) {
    error.value =
      reason instanceof ApiError
        ? reason
        : new ApiError({
            code: "AI_EDIT_FAILED",
            message: "暂时无法生成修改建议。",
            requestId: "",
            status: 500,
          });
  } finally {
    generating.value = false;
  }
}

function apply(): void {
  if (result.value) {
    emit("apply", [...result.value.commands]);
    result.value = null;
  }
}

onMounted(() => void loadAiStatus());
</script>

<template>
  <section class="ai-edit-panel" aria-label="AI 修改">
    <header class="ai-edit-panel__header">
      <div>
        <h2>AI 修改</h2>
        <p>{{ selectionLabel }}，修改会先预览，确认后才写入草稿。</p>
      </div>
    </header>

    <InlineNotice v-if="error" tone="error">
      <p>{{ error.message }}</p>
      <code v-if="error.requestId">{{ error.requestId }}</code>
    </InlineNotice>
    <InlineNotice v-if="aiStatus?.status === 'unconfigured'" tone="info">
      <p>AI 服务尚未配置，请使用右侧属性面板或 SQL 编辑器手动调整数据。</p>
    </InlineNotice>

    <form class="ai-edit-panel__form" @submit.prevent="submit">
      <label class="ai-panel__field ai-panel__field--wide">
        <span>修改要求</span>
        <textarea
          v-model="question"
          name="aiEditQuestion"
          rows="3"
          :disabled="generating"
          placeholder="例如：把标题改成华东销售分析，并把选中的图表移到右侧。"
          @input="formError = ''"
        />
      </label>
      <p v-if="formError" class="ai-panel__error">{{ formError }}</p>
      <button class="secondary-button" type="submit" :disabled="generating">
        {{ generating ? "正在生成预览…" : "生成修改预览" }}
      </button>
    </form>

    <section v-if="result" class="ai-edit-panel__result" aria-label="AI 修改预览">
      <div>
        <h3>修改预览</h3>
        <p>{{ result.explanation }}</p>
      </div>
      <ul class="ai-edit-panel__commands">
        <li v-for="(command, index) in result.commands" :key="`${command.type}-${index}`">
          {{ commandLabel(command) }}
        </li>
      </ul>
      <ul v-if="(result.warnings ?? []).length > 0" class="ai-panel__warnings">
        <li v-for="warning in result.warnings ?? []" :key="warning">{{ warning }}</li>
      </ul>
      <button
        class="primary-button"
        type="button"
        data-action="confirm-ai-edit"
        @click="apply"
      >
        应用修改
      </button>
    </section>
  </section>
</template>

<style scoped>
.ai-edit-panel {
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--dp-border-strong);
  border-radius: 8px;
  background: #fff;
}

.ai-edit-panel__header h2,
.ai-edit-panel__result h3 {
  margin: 0;
  font-size: 15px;
}

.ai-edit-panel__header p,
.ai-edit-panel__result p {
  margin: 6px 0 0;
  color: #5f5e5b;
  font-size: 12px;
  line-height: 1.5;
}

.ai-edit-panel h2,
.ai-edit-panel h3 {
  color: var(--dp-text);
}

.ai-edit-panel .ai-panel__field {
  display: grid;
  min-width: 0;
  gap: 6px;
}

.ai-edit-panel .ai-panel__field > span {
  color: var(--dp-text);
  font-size: 13px;
}

.ai-edit-panel .ai-panel__field textarea {
  box-sizing: border-box;
  width: 100%;
}

.ai-edit-panel .ai-panel__field textarea::placeholder {
  color: #6b6a67;
}

.ai-edit-panel .ai-panel__error {
  margin: 0;
  color: #b42318;
  font-size: 13px;
}

.ai-edit-panel__form,
.ai-edit-panel__result {
  display: grid;
  gap: 10px;
}

.ai-edit-panel__commands {
  display: grid;
  gap: 5px;
  margin: 0;
  padding-left: 18px;
  color: var(--dp-text);
  font-size: 12px;
}
</style>
