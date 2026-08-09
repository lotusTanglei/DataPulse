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
const datasetsLoading = ref(false);
const datasetsError = ref("");
const datasetId = ref("");
const dimension = ref("");
const measure = ref("");
const aggregation = ref<Aggregation>("sum");
const accent = ref("#3b82f6");
const background = ref("#0b1020");
const clickField = ref("");
const clickParameter = ref("");
const tableFields = ref<string[]>([]);
const componentBackground = ref("transparent");
const componentTextColor = ref("#f8fafc");
const componentBorderColor = ref("#3b82f6");
const componentBorderWidth = ref(0);
const componentBorderRadius = ref(0);
const componentOpacity = ref(1);
const refreshMode = ref<"disabled" | "interval">("disabled");
const refreshInterval = ref<10 | 30 | 60 | 300>(30);
const activeTab = ref<InspectorTab>("base");
const selectedId = computed(() =>
  store.selection.length === 1 ? store.selection[0] ?? null : null,
);
const selected = computed(() => {
  if (!selectedId.value) {
    return null;
  }
  return store.document?.components?.find(
    (component) => component.id === selectedId.value,
  ) ?? null;
});
const selectedDataset = computed(() =>
  datasets.value.find((item) => item.id === datasetId.value),
);
const fields = computed(() => selectedDataset.value?.definition.fields ?? []);
const measureFields = computed(() =>
  aggregation.value === "count"
    ? fields.value
    : fields.value.filter((field) =>
        ["integer", "number"].includes(field.data_type),
      ),
);
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
const isTable = computed(() => selectedDefinition.value?.dataCapability === "table");

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
  tableFields.value = [
    ...(chartSpec?.dimensions ?? []),
    ...(chartSpec?.measures?.map((item) => item.field) ?? []),
  ].filter((field, index, values) =>
    availableFields.includes(field) && values.indexOf(field) === index,
  );

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

  const style = selected.value?.style ?? {};
  componentBackground.value = typeof style.background_color === "string"
    ? style.background_color
    : "transparent";
  componentTextColor.value = typeof style.text_color === "string"
    ? style.text_color
    : "#f8fafc";
  componentBorderColor.value = typeof style.border_color === "string"
    ? style.border_color
    : "#3b82f6";
  componentBorderWidth.value = typeof style.border_width === "number"
    ? style.border_width
    : 0;
  componentBorderRadius.value = typeof style.border_radius === "number"
    ? style.border_radius
    : 0;
  componentOpacity.value = typeof style.opacity === "number"
    ? style.opacity
    : 1;
  refreshMode.value = store.document?.refresh?.mode ?? "disabled";
  refreshInterval.value = store.document?.refresh?.interval_seconds ?? 30;
}

watch([selected, datasets], syncInspectorFromSelection, { immediate: true });

watch(selectedId, () => {
  activeTab.value = supportsData.value ? "data" : "base";
});

watch(datasetId, () => {
  if (persistedChartSpec.value?.dataset_id === datasetId.value) {
    return;
  }
  dimension.value = fields.value[0]?.name ?? "";
  measure.value = fields.value[1]?.name ?? fields.value[0]?.name ?? "";
  clickField.value = dimension.value;
  tableFields.value = fields.value.slice(0, 2).map((field) => field.name);
});

watch(measureFields, (available) => {
  if (!available.some((field) => field.name === measure.value)) {
    measure.value = available[0]?.name ?? "";
  }
});

async function loadAvailableDatasets(): Promise<void> {
  datasetsLoading.value = true;
  datasetsError.value = "";
  try {
    datasets.value = await listDatasets();
  } catch {
    datasets.value = [];
    datasetsError.value = "数据集列表加载失败，请重试。";
  } finally {
    datasetsLoading.value = false;
  }
}

onMounted(loadAvailableDatasets);

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

function applyDataBinding(): void {
  if (!selected.value || !selectedDataset.value) {
    return;
  }
  if (isTable.value) {
    const selectedFields = fields.value
      .map((field) => field.name)
      .filter((field) => tableFields.value.includes(field));
    if (selectedFields.length === 0) {
      throw new Error("请至少选择一个表格字段。");
    }
    store.dispatch({
      type: "update_data_binding",
      component_id: selected.value.id,
      data_binding: {
        chart_spec: {
          schema_version: 1,
          dataset_id: selectedDataset.value.id,
          dimensions: selectedFields,
          measures: [],
          filters: [],
          sort: [],
          limit: selectedDataset.value.definition.max_rows,
          visual: { type: "table", title: "" },
        },
      },
    });
    return;
  }
  bindChart({
    datasetId: datasetId.value,
    dimension: dimension.value,
    measure: measure.value,
    aggregation: aggregation.value,
  });
}

function updateFrame(
  field: "x" | "y" | "width" | "height",
  value: number,
): void {
  if (!selected.value || !store.document || !Number.isFinite(value)) {
    return;
  }
  const frame = selected.value.frame;
  const canvas = store.document.canvas;
  const width = field === "width"
    ? Math.min(canvas.width, Math.max(40, value))
    : frame.width;
  const height = field === "height"
    ? Math.min(canvas.height, Math.max(40, value))
    : frame.height;
  const nextValue = field === "x"
    ? Math.min(Math.max(0, value), canvas.width - width)
    : field === "y"
      ? Math.min(Math.max(0, value), canvas.height - height)
      : field === "width"
        ? Math.min(width, canvas.width - frame.x)
        : Math.min(height, canvas.height - frame.y);
  store.dispatch({
    type: "update_frame",
    component_ids: [selected.value.id],
    patch: { [field]: nextValue },
  });
}

function toggleComponentState(field: "locked" | "hidden"): void {
  if (!selected.value) return;
  store.dispatch({
    type: "set_component_state",
    component_ids: [selected.value.id],
    patch: { [field]: !selected.value.state?.[field] },
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

function applyComponentStyle(): void {
  if (!selected.value) return;
  store.dispatch({
    type: "update_style",
    component_id: selected.value.id,
    patch: {
      background_color: componentBackground.value.trim() || "transparent",
      text_color: componentTextColor.value,
      border_color: componentBorderColor.value,
      border_width: Math.max(0, componentBorderWidth.value),
      border_radius: Math.max(0, componentBorderRadius.value),
      opacity: Math.min(1, Math.max(0, componentOpacity.value)),
    },
  });
}

function applyRefresh(): void {
  store.dispatch({
    type: "update_refresh",
    refresh: refreshMode.value === "interval"
      ? { mode: "interval", interval_seconds: refreshInterval.value }
      : { mode: "disabled", interval_seconds: null },
  });
}

function duplicateComponent(): void {
  if (!selected.value) return;
  const newId = crypto.randomUUID();
  store.dispatch({
    type: "duplicate_components",
    source_ids: [selected.value.id],
    id_map: { [selected.value.id]: newId },
  });
  store.selection = [newId];
}

function deleteComponent(): void {
  if (!selected.value) return;
  store.dispatch({
    type: "remove_components",
    component_ids: [selected.value.id],
  });
  store.selection = [];
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
            data-frame-field="x"
            type="number"
            :value="selected.frame.x"
            @change="updateFrame('x', Number(($event.target as HTMLInputElement).value))"
          />
        </label>
        <label>
          Y
          <input
            data-frame-field="y"
            type="number"
            :value="selected.frame.y"
            @change="updateFrame('y', Number(($event.target as HTMLInputElement).value))"
          />
        </label>
        <label>
          宽度
          <input
            data-frame-field="width"
            type="number"
            min="40"
            :value="selected.frame.width"
            @change="updateFrame('width', Number(($event.target as HTMLInputElement).value))"
          />
        </label>
        <label>
          高度
          <input
            data-frame-field="height"
            type="number"
            min="40"
            :value="selected.frame.height"
            @change="updateFrame('height', Number(($event.target as HTMLInputElement).value))"
          />
        </label>
        <div class="inspector-component-actions inspector-field--wide">
          <button
            class="secondary-button"
            data-component-lock
            type="button"
            @click="toggleComponentState('locked')"
          >
            {{ selected.state?.locked ? "解锁组件" : "锁定组件" }}
          </button>
          <button
            class="secondary-button"
            data-component-hide
            type="button"
            @click="toggleComponentState('hidden')"
          >
            {{ selected.state?.hidden ? "显示组件" : "隐藏组件" }}
          </button>
          <button
            class="secondary-button"
            data-component-duplicate
            type="button"
            @click="duplicateComponent"
          >
            复制组件
          </button>
          <button
            class="secondary-button is-danger"
            data-component-delete
            type="button"
            @click="deleteComponent"
          >
            删除组件
          </button>
        </div>
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
        <p v-if="datasetsLoading" class="inspector-field--wide" role="status">正在加载数据集…</p>
        <div v-else-if="datasetsError" class="inspector-inline-error inspector-field--wide" role="alert">
          <span>{{ datasetsError }}</span>
          <button class="table-action" type="button" @click="loadAvailableDatasets">重试</button>
        </div>
        <label class="inspector-field--wide">
          数据集
          <select v-model="datasetId" data-inspector-dataset>
            <option value="">请选择</option>
            <option v-for="dataset in datasets" :key="dataset.id" :value="dataset.id">
              {{ dataset.name }}
            </option>
          </select>
        </label>
        <fieldset v-if="isTable" class="inspector-table-fields inspector-field--wide">
          <legend>展示字段</legend>
          <label v-for="field in fields" :key="field.name">
            <input
              v-model="tableFields"
              type="checkbox"
              :value="field.name"
              :data-table-field="field.name"
            />
            <span>{{ field.name }}</span>
          </label>
        </fieldset>
        <label v-if="!isTable">
          维度
          <select v-model="dimension" data-inspector-dimension>
            <option v-for="field in fields" :key="field.name" :value="field.name">
              {{ field.name }}
            </option>
          </select>
        </label>
        <label v-if="!isTable">
          指标
          <select v-model="measure" data-inspector-measure>
            <option v-for="field in measureFields" :key="field.name" :value="field.name">
              {{ field.name }}
            </option>
          </select>
        </label>
        <label v-if="!isTable" class="inspector-field--wide">
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
          :disabled="!datasetId || (isTable ? tableFields.length === 0 : !dimension || !measure)"
          @click="applyDataBinding"
        >
          应用数据绑定
        </button>
        <p class="inspector-field--wide">应用后画布会立即查询并显示草稿数据；也可使用顶部“刷新数据”重新查询。</p>
      </div>
      <div v-show="activeTab === 'style'" class="inspector-section">
        <strong>组件外观</strong>
        <label class="inspector-field--wide">
          背景色
          <input
            v-model="componentBackground"
            data-style-field="background_color"
            type="text"
            placeholder="transparent 或 #0b1020"
          />
        </label>
        <label>
          文字色
          <input v-model="componentTextColor" data-style-field="text_color" type="color" />
        </label>
        <label>
          边框色
          <input v-model="componentBorderColor" data-style-field="border_color" type="color" />
        </label>
        <label>
          边框
          <input v-model.number="componentBorderWidth" data-style-field="border_width" type="number" min="0" />
        </label>
        <label>
          圆角
          <input v-model.number="componentBorderRadius" data-style-field="border_radius" type="number" min="0" />
        </label>
        <label class="inspector-field--wide">
          透明度
          <input v-model.number="componentOpacity" data-style-field="opacity" type="range" min="0" max="1" step="0.05" />
        </label>
        <button
          class="secondary-button inspector-field--wide"
          data-apply-component-style
          type="button"
          @click="applyComponentStyle"
        >
          应用组件样式
        </button>
        <strong>画布主题</strong>
        <label>
          强调色
          <input v-model="accent" data-theme-accent type="color" />
        </label>
        <label>
          背景色
          <input v-model="background" data-theme-background type="color" />
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
        <label class="inspector-field--wide">
          数据刷新
          <select v-model="refreshMode" data-refresh-mode>
            <option value="disabled">手动刷新</option>
            <option value="interval">定时刷新</option>
          </select>
        </label>
        <label v-if="refreshMode === 'interval'" class="inspector-field--wide">
          刷新间隔
          <select v-model.number="refreshInterval" data-refresh-interval>
            <option :value="10">10 秒</option>
            <option :value="30">30 秒</option>
            <option :value="60">1 分钟</option>
            <option :value="300">5 分钟</option>
          </select>
        </label>
        <button
          class="secondary-button inspector-field--wide"
          data-apply-refresh
          type="button"
          @click="applyRefresh"
        >
          应用刷新策略
        </button>
        <p>刷新策略作用于整张大屏，编辑、预览和发布播放使用同一份配置。</p>
      </div>
    </template>
  </section>
</template>
