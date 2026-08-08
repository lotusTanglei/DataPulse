<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import type { ChartSpec } from "../../../contracts";
import { listDatasets } from "../../datasets/api";
import type { Dataset } from "../../datasets/types";
import { defaultComponentRegistry } from "../../runtime/registry";
import type { JsonValue } from "../../query/types";
import { useScreenEditorStore } from "./store";

type Aggregation = "sum" | "avg" | "min" | "max" | "count";
type InspectorTab = "base" | "data" | "style" | "interaction" | "advanced";

const store = useScreenEditorStore();
const datasets = ref<Dataset[]>([]);
const datasetId = ref("");
const dimension = ref("");
const measure = ref("");
const aggregation = ref<Aggregation>("sum");
const accent = ref("#3b82f6");
const background = ref("#0b1020");
const clickField = ref("");
const clickParameter = ref("");
const activeTab = ref<InspectorTab>("base");
const selected = computed(() => {
  if (store.selection.length !== 1) {
    return null;
  }
  return store.document?.components?.find(
    (component) => component.id === store.selection[0],
  ) ?? null;
});
const selectedDataset = computed(() =>
  datasets.value.find((item) => item.id === datasetId.value),
);
const fields = computed(() => selectedDataset.value?.definition.fields ?? []);
const selectedDefinition = computed(() =>
  selected.value
    ? defaultComponentRegistry.get(selected.value.type)
    : undefined,
);
const supportsData = computed(
  () => selectedDefinition.value?.dataCapability !== "none",
);
const supportsInteraction = computed(() =>
  ["series", "geo"].includes(selectedDefinition.value?.dataCapability ?? ""),
);

const persistedChartSpec = computed<ChartSpec | null>(() => {
  const value = selected.value?.data_binding?.chart_spec;
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as unknown as ChartSpec;
});

function syncInspectorFromSelection(): void {
  const chartSpec = persistedChartSpec.value;
  datasetId.value = typeof chartSpec?.dataset_id === "string"
    ? chartSpec.dataset_id
    : "";

  const availableFields = fields.value.map((field) => field.name);
  const persistedDimension = chartSpec?.dimensions?.[0];
  const persistedMeasure = chartSpec?.measures?.[0]?.field;
  dimension.value = availableFields.includes(persistedDimension ?? "")
    ? persistedDimension!
    : availableFields[0] ?? "";
  measure.value = availableFields.includes(persistedMeasure ?? "")
    ? persistedMeasure!
    : availableFields[1] ?? availableFields[0] ?? "";
  aggregation.value = chartSpec?.measures?.[0]?.aggregation ?? "sum";

  const clickInteraction = selected.value?.interactions?.find(
    (interaction) =>
      interaction.event === "click" && interaction.action === "set_parameter",
  );
  clickField.value = clickInteraction?.field ?? dimension.value;
  clickParameter.value = clickInteraction?.parameter ?? "";

  const accentToken = store.document?.theme?.tokens?.screen_accent;
  const backgroundColor = store.document?.canvas?.background?.color;
  accent.value = typeof accentToken === "string" ? accentToken : "#3b82f6";
  background.value =
    typeof backgroundColor === "string" ? backgroundColor : "#0b1020";
}

watch([selected, datasets], syncInspectorFromSelection, { immediate: true });

watch(selected, () => {
  activeTab.value = supportsData.value ? "data" : "base";
});

watch(datasetId, () => {
  if (persistedChartSpec.value?.dataset_id === datasetId.value) {
    return;
  }
  dimension.value = fields.value[0]?.name ?? "";
  measure.value = fields.value[1]?.name ?? fields.value[0]?.name ?? "";
  clickField.value = dimension.value;
});

onMounted(async () => {
  try {
    datasets.value = await listDatasets();
  } catch {
    datasets.value = [];
  }
});

function visualType(type: string): string {
  return type.replace("builtin.", "");
}

function bindChart(input: {
  datasetId: string;
  dimension: string;
  measure: string;
  aggregation: Aggregation;
}): void {
  if (!selected.value) {
    return;
  }
  const dataset = datasets.value.find((item) => item.id === input.datasetId);
  const fields = new Set(
    dataset?.definition.fields.map((field) => field.name) ?? [],
  );
  if (!dataset || !fields.has(input.dimension) || !fields.has(input.measure)) {
    throw new Error("请选择有效的数据集字段。");
  }
  store.dispatch({
    type: "update_data_binding",
    component_id: selected.value.id,
    data_binding: {
      chart_spec: {
        schema_version: 1,
        dataset_id: dataset.id,
        dimensions: [input.dimension],
        measures: [{ field: input.measure, aggregation: input.aggregation }],
        filters: [],
        sort: [],
        limit: dataset.definition.max_rows,
        visual: { type: visualType(selected.value.type), title: "" },
      },
    },
  });
}

function updateTheme(accent: string, background: string): void {
  store.dispatch({
    type: "update_theme",
    patch: {
      tokens: {
        ...(store.document?.theme?.tokens ?? {}),
        screen_accent: accent,
      },
    },
  });
  store.dispatch({
    type: "update_canvas",
    patch: { background: { color: background } },
  });
}

function setClickInteraction(field: string, parameter: string): void {
  if (!selected.value) {
    return;
  }
  const knownParameter = store.document?.parameters?.some(
    (item) => item.name === parameter,
  );
  if (!knownParameter) {
    throw new Error("请选择已声明的全局参数。");
  }
  store.dispatch({
    type: "update_interactions",
    component_id: selected.value.id,
    interactions: [
      {
        event: "click",
        action: "set_parameter",
        field,
        parameter,
      },
    ],
  });
}

function updateProp(name: string, value: JsonValue): void {
  if (!selected.value) {
    return;
  }
  store.dispatch({
    type: "update_props",
    component_id: selected.value.id,
    patch: { [name]: value },
  });
}

defineExpose({ bindChart, setClickInteraction, updateTheme });
</script>

<template>
  <section class="inspector-panel" aria-label="属性面板">
    <h2>属性</h2>
    <p v-if="!selected" class="editor-panel-empty">选择一个组件后编辑属性。</p>
    <template v-else>
      <nav class="inspector-tabs" aria-label="属性分类">
        <button
          v-for="tab in [
            { id: 'base', label: '基础' },
            ...(supportsData ? [{ id: 'data', label: '数据' }] : []),
            { id: 'style', label: '样式' },
            ...(supportsInteraction ? [{ id: 'interaction', label: '交互' }] : []),
            { id: 'advanced', label: '高级' },
          ]"
          :key="tab.id"
          class="inspector-tab"
          :class="{ 'is-active': activeTab === tab.id }"
          type="button"
          :data-inspector-tab="tab.id"
          @click="activeTab = tab.id as InspectorTab"
        >
          {{ tab.label }}
        </button>
      </nav>
      <div v-show="activeTab === 'base'" class="inspector-section">
        <strong>{{ selected.type }}</strong>
        <label>
          X
          <input
            type="number"
            :value="selected.frame.x"
            @change="
              store.dispatch({
                type: 'update_frame',
                component_ids: [selected.id],
                patch: { x: Number(($event.target as HTMLInputElement).value) },
              })
            "
          />
        </label>
        <label>
          Y
          <input
            type="number"
            :value="selected.frame.y"
            @change="
              store.dispatch({
                type: 'update_frame',
                component_ids: [selected.id],
                patch: { y: Number(($event.target as HTMLInputElement).value) },
              })
            "
          />
        </label>
        <label
          v-if="selected.type === 'builtin.text'"
          class="inspector-field--wide"
        >
          文本内容
          <input
            type="text"
            :value="selected.props?.text"
            @change="
              updateProp(
                'text',
                ($event.target as HTMLInputElement).value,
              )
            "
          />
        </label>
        <label
          v-if="selected.type === 'builtin.image'"
          class="inspector-field--wide"
        >
          图片资源 ID
          <input
            type="text"
            :value="selected.props?.asset_id"
            @change="
              updateProp(
                'asset_id',
                ($event.target as HTMLInputElement).value,
              )
            "
          />
        </label>
      </div>
      <div v-if="supportsData" v-show="activeTab === 'data'" class="inspector-section">
        <strong>数据</strong>
        <label class="inspector-field--wide">
          数据集
          <select v-model="datasetId" data-inspector-dataset>
            <option value="">请选择</option>
            <option v-for="dataset in datasets" :key="dataset.id" :value="dataset.id">
              {{ dataset.name }}
            </option>
          </select>
        </label>
        <label>
          维度
          <select v-model="dimension" data-inspector-dimension>
            <option v-for="field in fields" :key="field.name" :value="field.name">
              {{ field.name }}
            </option>
          </select>
        </label>
        <label>
          指标
          <select v-model="measure" data-inspector-measure>
            <option v-for="field in fields" :key="field.name" :value="field.name">
              {{ field.name }}
            </option>
          </select>
        </label>
        <label class="inspector-field--wide">
          聚合
          <select v-model="aggregation" data-inspector-aggregation>
            <option value="sum">求和</option>
            <option value="avg">平均</option>
            <option value="min">最小</option>
            <option value="max">最大</option>
            <option value="count">计数</option>
          </select>
        </label>
        <button
          class="secondary-button inspector-field--wide"
          type="button"
          data-apply-binding
          :disabled="!datasetId || !dimension || !measure"
          @click="bindChart({ datasetId, dimension, measure, aggregation })"
        >
          应用数据绑定
        </button>
      </div>
      <div v-show="activeTab === 'style'" class="inspector-section">
        <strong>主题与背景</strong>
        <label>
          强调色
          <input v-model="accent" type="color" />
        </label>
        <label>
          背景色
          <input v-model="background" type="color" />
        </label>
        <button
          class="secondary-button inspector-field--wide"
          type="button"
          @click="updateTheme(accent, background)"
        >
          应用主题
        </button>
      </div>
      <div v-if="supportsInteraction" v-show="activeTab === 'interaction'" class="inspector-section">
        <strong>交互</strong>
        <label>
          点击字段
          <select v-model="clickField">
            <option v-for="field in fields" :key="field.name" :value="field.name">
              {{ field.name }}
            </option>
          </select>
        </label>
        <label>
          写入参数
          <select v-model="clickParameter">
            <option value="">请选择</option>
            <option
              v-for="parameter in store.document?.parameters ?? []"
              :key="parameter.name"
              :value="parameter.name"
            >
              {{ parameter.name }}
            </option>
          </select>
        </label>
        <button
          class="secondary-button inspector-field--wide"
          type="button"
          :disabled="!clickField || !clickParameter"
          @click="setClickInteraction(clickField, clickParameter)"
        >
          应用点击联动
        </button>
      </div>
      <div v-show="activeTab === 'advanced'" class="inspector-section inspector-advanced-hint">
        <strong>高级</strong>
        <p>组件级错误、刷新策略和事件动作将在此处逐步扩展。</p>
      </div>
    </template>
  </section>
</template>
