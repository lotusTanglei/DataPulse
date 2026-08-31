<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import type { ChartSpec } from "../../../contracts";
import { listDatasets } from "../../datasets/api";
import type { Dataset } from "../../datasets/types";
import { defaultComponentRegistry } from "../../runtime/registry";
import {
  createMockBinding,
  resolveLocalResult,
  type MockDataConfig,
} from "../../runtime/mockData";
import type { JsonValue } from "../../query/types";
import { resolveThemeTokens } from "../../runtime/theme";
import type { PropertyDefinition } from "../../runtime/types";
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
const themePanelBackground = ref("#0b1b2b");
const themePanelBackgroundAlt = ref("#10253a");
const themePanelBorder = ref("#1b4160");
const themeTextPrimary = ref("#edf7ff");
const themeTextSecondary = ref("#9ab3c8");
const themeChartGrid = ref("rgba(148, 163, 184, 0.14)");
const themeChartAxis = ref("#1b4160");
const themeChartColors = ref("#26d9c1, #3b8df4, #8a9ff0, #f3b638, #f16d75, #a5d85b");
const clickField = ref("");
const clickParameter = ref("");
const tableFields = ref<string[]>([]);
const componentBackground = ref("transparent");
const componentTextColor = ref("#f8fafc");
const componentBorderColor = ref("#3b82f6");
const componentBorderWidth = ref(0);
const componentBorderRadius = ref(0);
const componentOpacity = ref(1);
const staticDataJson = ref("[]");
const dataError = ref("");
const mockSeedInput = ref(42);
const mockRowCount = ref(8);
const mockSeriesCount = ref(2);
const mockCategoryCount = ref(6);
const mockValueMin = ref(0);
const mockValueMax = ref(100);
const mockTrend = ref<NonNullable<MockDataConfig["trend"]>>("up");
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
const propertyGroups = computed(() => selectedDefinition.value?.propertyGroups ?? []);
const supportsData = computed(
  () => selectedDefinition.value?.dataCapability !== "none",
);
const supportsInteraction = computed(() =>
  ["series", "geo"].includes(selectedDefinition.value?.dataCapability ?? ""),
);
const isTable = computed(() => selectedDefinition.value?.dataCapability === "table");
const bindingSource = computed<"dataset" | "static" | "mock" | "none">(() => {
  const binding = selected.value?.data_binding;
  if (binding?.source === "static") return "static";
  if (binding?.source === "mock") return "mock";
  if (binding?.chart_spec) return "dataset";
  return "none";
});
const localPreview = computed(() => {
  if (!selected.value || !["static", "mock"].includes(bindingSource.value)) {
    return null;
  }
  try {
    return resolveLocalResult(selected.value, selected.value.data_binding ?? {});
  } catch {
    return null;
  }
});
const mockSeed = computed(() => {
  const value = selected.value?.data_binding?.mock_data;
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return typeof value.seed === "number" ? Math.trunc(value.seed) : 42;
  }
  return 42;
});

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
  const themeTokens = resolveThemeTokens(store.document?.theme);
  const backgroundColor = store.document?.canvas?.background?.color;
  accent.value = typeof accentToken === "string"
    ? accentToken
    : typeof themeTokens.accent === "string" ? themeTokens.accent : "#3b82f6";
  background.value =
    typeof backgroundColor === "string" ? backgroundColor : "#0b1020";
  themePanelBackground.value = typeof themeTokens.panel_background === "string"
    ? themeTokens.panel_background
    : "#0b1b2b";
  themePanelBackgroundAlt.value = typeof themeTokens.panel_background_alt === "string"
    ? themeTokens.panel_background_alt
    : "#10253a";
  themePanelBorder.value = typeof themeTokens.panel_border === "string"
    ? themeTokens.panel_border
    : "#1b4160";
  themeTextPrimary.value = typeof themeTokens.text_primary === "string"
    ? themeTokens.text_primary
    : "#edf7ff";
  themeTextSecondary.value = typeof themeTokens.text_secondary === "string"
    ? themeTokens.text_secondary
    : "#9ab3c8";
  themeChartGrid.value = typeof themeTokens.chart_grid === "string"
    ? themeTokens.chart_grid
    : "rgba(148, 163, 184, 0.14)";
  themeChartAxis.value = typeof themeTokens.chart_axis === "string"
    ? themeTokens.chart_axis
    : "#1b4160";
  themeChartColors.value = Array.isArray(themeTokens.chart_colors)
    ? themeTokens.chart_colors.filter((value): value is string => typeof value === "string").join(", ")
    : "#26d9c1, #3b8df4, #8a9ff0, #f3b638, #f16d75, #a5d85b";

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
  staticDataJson.value = JSON.stringify(
    selected.value?.data_binding?.static_data ?? [],
    null,
    2,
  );
  const mockData = selected.value?.data_binding?.mock_data;
  const mock = mockData !== null && typeof mockData === "object" && !Array.isArray(mockData)
    ? mockData
    : {};
  mockSeedInput.value = typeof mock.seed === "number" ? Math.trunc(mock.seed) : 42;
  mockRowCount.value = typeof mock.row_count === "number" ? Math.trunc(mock.row_count) : 8;
  mockSeriesCount.value = typeof mock.series_count === "number" ? Math.trunc(mock.series_count) : 2;
  mockCategoryCount.value = typeof mock.category_count === "number" ? Math.trunc(mock.category_count) : 6;
  mockValueMin.value = typeof mock.value_min === "number" ? mock.value_min : 0;
  mockValueMax.value = typeof mock.value_max === "number" ? mock.value_max : 100;
  mockTrend.value = mock.trend === "down" || mock.trend === "flat" ? mock.trend : "up";
  dataError.value = "";
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
  const typeMap: Record<string, string> = {
    "builtin.digital_number": "kpi",
    "builtin.gauge": "gauge",
    "builtin.ranking": "table",
    "builtin.alert_list": "table",
    "builtin.status_matrix": "table",
    "builtin.timeline": "table",
  };
  return typeMap[type] ?? type.replace("builtin.", "");
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

function applyMockData(seed = mockSeedInput.value): void {
  if (!selected.value) return;
  const binding = createMockBinding(selected.value.type, Math.trunc(seed));
  const mockData = binding.mock_data !== null && typeof binding.mock_data === "object" && !Array.isArray(binding.mock_data)
    ? binding.mock_data
    : {};
  const rawMin = Number.isFinite(mockValueMin.value) ? mockValueMin.value : 0;
  const rawMax = Number.isFinite(mockValueMax.value) ? mockValueMax.value : 100;
  const min = Math.min(rawMin, rawMax);
  dataError.value = "";
  store.dispatch({
    type: "update_data_binding",
    component_id: selected.value.id,
    data_binding: {
      ...binding,
      mock_data: {
        ...mockData,
        seed: Math.trunc(seed),
        row_count: Math.min(100, Math.max(1, Math.trunc(mockRowCount.value))),
        series_count: Math.min(3, Math.max(1, Math.trunc(mockSeriesCount.value))),
        category_count: Math.min(10, Math.max(3, Math.trunc(mockCategoryCount.value))),
        value_min: min,
        value_max: Math.max(min, rawMax),
        trend: mockTrend.value,
      },
    },
  });
}

function regenerateMockData(): void {
  mockSeedInput.value = mockSeed.value + 1;
  applyMockData(mockSeedInput.value);
}

function clearDataBinding(): void {
  if (!selected.value) return;
  dataError.value = "";
  store.dispatch({
    type: "update_data_binding",
    component_id: selected.value.id,
    data_binding: {},
  });
}

function selectDatasetSource(): void {
  dataError.value = "";
  if (bindingSource.value === "mock" || bindingSource.value === "static") {
    clearDataBinding();
  }
}

function startStaticData(): void {
  if (staticDataJson.value === "[]") {
    staticDataJson.value = '[{\n  "类别": "示例",\n  "数值": 100\n}]';
  }
  applyStaticData();
}

function isScalar(value: unknown): value is JsonValue {
  return value === null || typeof value === "string" || typeof value === "number" || typeof value === "boolean";
}

function staticDataFromInput(value: unknown): Record<string, JsonValue> {
  const payload = value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as { columns?: unknown; rows?: unknown }
    : { rows: value };
  if (!Array.isArray(payload.rows)) {
    throw new Error("固定数据需要是一层对象数组，或包含 rows 的数据结构。");
  }
  const canonicalColumns = Array.isArray(payload.columns)
    ? payload.columns.map((column) => {
        if (typeof column === "string") {
          return { name: column, data_type: "string" };
        }
        const item = column !== null && typeof column === "object" && !Array.isArray(column)
          ? column as { name?: unknown; data_type?: unknown }
          : {};
        return {
          name: typeof item.name === "string" ? item.name : "",
          data_type: typeof item.data_type === "string" ? item.data_type : "string",
        };
      })
    : [];
  if (canonicalColumns.length > 0 && payload.rows.every((row) => Array.isArray(row))) {
    if (canonicalColumns.length > 20 || canonicalColumns.some((column) => !column.name.trim()) || payload.rows.length > 500) {
      throw new Error("固定数据需要包含 1-20 列和不超过 500 行。");
    }
    const rows = payload.rows.map((row) => {
      if (!Array.isArray(row) || row.length !== canonicalColumns.length || row.some((item) => !isScalar(item))) {
        throw new Error("固定数据行与字段数量不一致，且每个单元格必须是标量。");
      }
      return row as JsonValue[];
    });
    return { schema_version: 1, columns: canonicalColumns, rows };
  }
  const objects = payload.rows.filter(
    (item): item is Record<string, unknown> =>
      item !== null && typeof item === "object" && !Array.isArray(item),
  );
  if (objects.length !== payload.rows.length) {
    throw new Error("固定数据每一行必须是一层对象。");
  }
  const names = Array.isArray(payload.columns)
    ? payload.columns.map((column) =>
        column !== null && typeof column === "object" && typeof (column as { name?: unknown }).name === "string"
          ? (column as { name: string }).name
          : typeof column === "string" ? column : "",
      )
    : [...new Set(objects.flatMap((row) => Object.keys(row)))];
  const columnNames = names.filter((name, index) => name.trim() && names.indexOf(name) === index);
  if (columnNames.length === 0 || columnNames.length > 20 || objects.length > 500) {
    throw new Error("固定数据需要包含 1-20 列和不超过 500 行。");
  }
  const rows = objects.map((row) =>
    columnNames.map((name) => {
      const item = row[name];
      if (!isScalar(item)) {
        throw new Error("固定数据单元格必须是字符串、数字、布尔值或空值。");
      }
      return item;
    }),
  );
  const columns = columnNames.map((name) => ({
    name,
    data_type: rows.every((row) => typeof row[columnNames.indexOf(name)] === "number") ? "number" : "string",
  }));
  return { schema_version: 1, columns, rows };
}

function applyStaticData(): void {
  if (!selected.value) return;
  try {
    const data = staticDataFromInput(JSON.parse(staticDataJson.value));
    dataError.value = "";
    store.dispatch({
      type: "update_data_binding",
      component_id: selected.value.id,
      data_binding: { source: "static", static_data: data },
    });
  } catch (error) {
    dataError.value = error instanceof Error ? error.message : "固定数据格式无效。";
  }
}

function materializeMockData(): void {
  if (!selected.value || bindingSource.value !== "mock") return;
  try {
    const result = resolveLocalResult(selected.value, selected.value.data_binding ?? {});
    if (!result) throw new Error("演示数据尚未生成。");
    dataError.value = "";
    store.dispatch({
      type: "update_data_binding",
      component_id: selected.value.id,
      data_binding: {
        source: "static",
        static_data: {
          schema_version: 1,
          columns: result.columns.map(({ name, data_type }) => ({ name, data_type })),
          rows: result.rows,
        },
      },
    });
  } catch (error) {
    dataError.value = error instanceof Error ? error.message : "演示数据无法转换。";
  }
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

function propertyValue(property: PropertyDefinition): JsonValue {
  const value = selected.value?.props?.[property.name];
  return value !== undefined ? value : property.defaultValue ?? "";
}

function propertyTextValue(property: PropertyDefinition): string {
  const value = propertyValue(property);
  if (value === null) return "";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

function updatePropertyFromEvent(property: PropertyDefinition, event: Event): void {
  const target = event.target as HTMLInputElement | HTMLSelectElement;
  let value: JsonValue;
  if (property.editor === "boolean") {
    value = (target as HTMLInputElement).checked;
  } else if (property.editor === "number") {
    const number = Number(target.value);
    if (!Number.isFinite(number)) return;
    value = Math.min(
      property.max ?? number,
      Math.max(property.min ?? number, number),
    );
  } else {
    value = target.value;
  }
  updateProp(property.name, value);
}

function toggleComponentState(field: "locked" | "hidden"): void {
  if (!selected.value) return;
  store.dispatch({
    type: "set_component_state",
    component_ids: [selected.value.id],
    patch: { [field]: !selected.value.state?.[field] },
  });
}

function updateTheme(nextAccent: string, nextBackground: string): void {
  const chartColors = themeChartColors.value
    .split(",")
    .map((color) => color.trim())
    .filter(Boolean)
    .slice(0, 12);
  store.dispatch({
    type: "update_theme",
    patch: {
      tokens: {
        ...(store.document?.theme?.tokens ?? {}),
        accent: nextAccent,
        screen_accent: nextAccent,
        panel_background: themePanelBackground.value,
        panel_background_alt: themePanelBackgroundAlt.value,
        panel_border: themePanelBorder.value,
        text_primary: themeTextPrimary.value,
        text_secondary: themeTextSecondary.value,
        chart_grid: themeChartGrid.value,
        chart_axis: themeChartAxis.value,
        chart_colors: chartColors.length > 0 ? chartColors : ["#26d9c1"],
      },
    },
  });
  store.dispatch({
    type: "update_canvas",
    patch: { background: { color: nextBackground } },
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
        <div
          v-for="group in propertyGroups"
          :key="group.id"
          class="inspector-property-group inspector-field--wide"
        >
          <div class="inspector-property-group__heading">
            <strong>{{ group.label }}</strong>
          </div>
          <label
            v-for="property in group.properties"
            :key="property.name"
            class="inspector-property"
            :class="{
              'inspector-field--wide': property.wide,
              'inspector-property--boolean': property.editor === 'boolean',
            }"
            :data-property-name="property.name"
          >
            <input
              v-if="property.editor === 'boolean'"
              type="checkbox"
              :checked="propertyValue(property) === true"
              @change="updatePropertyFromEvent(property, $event)"
            />
            <span v-if="property.editor === 'boolean'">{{ property.label }}</span>
            <template v-else>
              <span>{{ property.label }}</span>
              <select
                v-if="property.editor === 'select'"
                :value="propertyTextValue(property)"
                @change="updatePropertyFromEvent(property, $event)"
              >
                <option
                  v-for="option in property.options ?? []"
                  :key="String(option.value)"
                  :value="String(option.value)"
                >
                  {{ option.label }}
                </option>
              </select>
              <input
                v-else
                :type="property.editor"
                :value="propertyTextValue(property)"
                :min="property.min"
                :max="property.max"
                :step="property.step"
                :placeholder="property.placeholder"
                @change="updatePropertyFromEvent(property, $event)"
              />
            </template>
          </label>
        </div>
      </div>
      <div v-if="supportsData" v-show="activeTab === 'data'" class="inspector-section">
        <div class="inspector-section__heading">
          <strong>数据</strong>
          <span class="inspector-source-state" :data-source="bindingSource">
            {{ bindingSource === "dataset" ? "数据集" : bindingSource === "static" ? "固定数据" : bindingSource === "mock" ? "演示数据" : "未绑定" }}
          </span>
        </div>
        <div class="inspector-data-modes inspector-field--wide" role="group" aria-label="数据来源">
          <button
            type="button"
            :class="{ 'is-active': bindingSource === 'dataset' || bindingSource === 'none' }"
            data-data-source="dataset"
            @click="selectDatasetSource"
          >
            数据集
          </button>
          <button
            type="button"
            :class="{ 'is-active': bindingSource === 'mock' }"
            data-data-source="mock"
            @click="applyMockData()"
          >
            演示数据
          </button>
          <button
            type="button"
            :class="{ 'is-active': bindingSource === 'static' }"
            data-data-source="static"
            @click="startStaticData"
          >
            固定数据
          </button>
        </div>
        <p class="inspector-field--wide inspector-data-hint">
          没有数据源时使用演示数据完成布局；演示数据不发起接口请求。
        </p>
        <div v-if="bindingSource === 'mock'" class="inspector-local-data inspector-field--wide">
          <div class="inspector-local-data__meta">
            <span>Seed {{ mockSeed }}</span>
            <span v-if="localPreview">{{ localPreview.row_count }} 行 · {{ localPreview.columns.length }} 列</span>
          </div>
          <div class="inspector-mock-controls">
            <label>
              Seed
              <input v-model.number="mockSeedInput" type="number" data-mock-seed />
            </label>
            <label>
              行数
              <input v-model.number="mockRowCount" type="number" min="1" max="100" data-mock-row-count />
            </label>
            <label v-if="selectedDefinition?.demoDataKind === 'series'">
              序列数
              <input v-model.number="mockSeriesCount" type="number" min="1" max="3" data-mock-series-count />
            </label>
            <label v-if="selectedDefinition?.demoDataKind === 'ranking'">
              类别数
              <input v-model.number="mockCategoryCount" type="number" min="3" max="10" data-mock-category-count />
            </label>
            <label>
              数值下限
              <input v-model.number="mockValueMin" type="number" data-mock-value-min />
            </label>
            <label>
              数值上限
              <input v-model.number="mockValueMax" type="number" data-mock-value-max />
            </label>
            <label v-if="selectedDefinition?.demoDataKind === 'series'" class="inspector-field--wide">
              趋势
              <select v-model="mockTrend" data-mock-trend>
                <option value="up">上升</option>
                <option value="flat">平稳</option>
                <option value="down">下降</option>
              </select>
            </label>
          </div>
          <div class="inspector-component-actions">
            <button class="secondary-button" type="button" data-regenerate-demo @click="regenerateMockData">
              重新生成
            </button>
            <button class="secondary-button" type="button" data-apply-demo @click="applyMockData()">
              应用参数
            </button>
            <button class="secondary-button" type="button" data-materialize-demo @click="materializeMockData">
              转为固定数据
            </button>
          </div>
        </div>
        <template v-else-if="bindingSource === 'static'">
          <label class="inspector-field--wide">
            JSON 数据
            <textarea v-model="staticDataJson" rows="8" data-static-data-json spellcheck="false" />
          </label>
          <button class="secondary-button inspector-field--wide" type="button" data-apply-static @click="applyStaticData">
            应用固定数据
          </button>
        </template>
        <div v-if="dataError" class="inspector-inline-error inspector-field--wide" role="alert">
          {{ dataError }}
        </div>
        <template v-if="bindingSource === 'dataset' || bindingSource === 'none'">
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
        </template>
        <button
          v-if="bindingSource !== 'none'"
          class="table-action inspector-field--wide"
          type="button"
          data-clear-data-binding
          @click="clearDataBinding"
        >
          清除当前数据绑定
        </button>
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
        <div class="inspector-theme-grid inspector-field--wide">
          <label>
            面板背景
            <input v-model="themePanelBackground" data-theme-panel-background type="color" />
          </label>
          <label>
            面板层次
            <input v-model="themePanelBackgroundAlt" data-theme-panel-background-alt type="color" />
          </label>
          <label>
            面板边框
            <input v-model="themePanelBorder" data-theme-panel-border type="color" />
          </label>
          <label>
            主文字
            <input v-model="themeTextPrimary" data-theme-text-primary type="color" />
          </label>
          <label>
            次文字
            <input v-model="themeTextSecondary" data-theme-text-secondary type="color" />
          </label>
        </div>
        <label class="inspector-field--wide">
          图表网格线
          <input v-model="themeChartGrid" data-theme-chart-grid type="text" placeholder="rgba(148, 163, 184, 0.14)" />
        </label>
        <label class="inspector-field--wide">
          图表坐标轴
          <input v-model="themeChartAxis" data-theme-chart-axis type="text" placeholder="#1b4160" />
        </label>
        <label class="inspector-field--wide">
          图表色板
          <input v-model="themeChartColors" data-theme-chart-colors type="text" placeholder="#26d9c1, #3b8df4" />
        </label>
        <button
          class="secondary-button inspector-field--wide"
          data-apply-theme
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
