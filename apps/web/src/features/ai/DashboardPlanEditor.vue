<script setup lang="ts">
import { Plus, Trash2 } from "@lucide/vue";
import { ref, toRaw, watch } from "vue";

import type { DashboardPlan } from "../../contracts";

const props = defineProps<{ modelValue: DashboardPlan }>();
const emit = defineEmits<{ "update:modelValue": [value: DashboardPlan] }>();

type EditableMeasure = {
  field: string;
  aggregation: "sum" | "avg" | "min" | "max" | "count";
};

type EditableWidget = {
  id: string;
  title: string;
  dataset_id: string;
  chart_type: (typeof chartTypes)[number];
  region_id: string;
  measures: EditableMeasure[];
  [key: string]: unknown;
};

type EditablePlan = {
  title: string;
  narrative: string;
  regions: Array<{ id: string; title?: string }>;
  widgets: EditableWidget[];
  [key: string]: unknown;
};

const chartTypes = [
  "area",
  "bar",
  "funnel",
  "gauge",
  "heatmap",
  "kpi",
  "line",
  "map",
  "pie",
  "progress",
  "radar",
  "scatter",
  "table",
] as const;

function clonePlan(value: DashboardPlan | EditablePlan): EditablePlan {
  return structuredClone(toRaw(value)) as unknown as EditablePlan;
}

const draft = ref<EditablePlan>(clonePlan(props.modelValue));

watch(
  () => props.modelValue,
  (value) => {
    draft.value = clonePlan(value);
  },
  { deep: true },
);

function commit(): void {
  emit(
    "update:modelValue",
    clonePlan(draft.value) as unknown as DashboardPlan,
  );
}

function addMeasure(widgetIndex: number): void {
  const widget = draft.value.widgets[widgetIndex];
  if (!widget) {
    return;
  }
  widget.measures = [...(widget.measures ?? []), { field: "", aggregation: "sum" }];
  commit();
}

function removeMeasure(widgetIndex: number, measureIndex: number): void {
  const widget = draft.value.widgets[widgetIndex];
  if (!widget) {
    return;
  }
  widget.measures = (widget.measures ?? []).filter((_, index) => index !== measureIndex);
  commit();
}
</script>

<template>
  <section class="plan-editor" aria-label="大屏规划">
    <header class="plan-editor__heading">
      <div>
        <h3>{{ draft.title }}</h3>
        <p>{{ draft.narrative }}</p>
      </div>
      <span>{{ draft.widgets.length }} 个组件</span>
    </header>

    <article
      v-for="(widget, widgetIndex) in draft.widgets"
      :key="widget.id"
      class="plan-widget"
    >
      <div class="plan-widget__heading">
        <strong>{{ widget.title }}</strong>
        <code>{{ widget.dataset_id }}</code>
      </div>

      <div class="plan-widget__controls">
        <label>
          <span>图表</span>
          <select v-model="widget.chart_type" data-field="chart-type" @change="commit">
            <option v-for="chartType in chartTypes" :key="chartType" :value="chartType">
              {{ chartType }}
            </option>
          </select>
        </label>
        <label>
          <span>分区</span>
          <select v-model="widget.region_id" data-field="region" @change="commit">
            <option v-for="region in draft.regions" :key="region.id" :value="region.id">
              {{ region.title || region.id }}
            </option>
          </select>
        </label>
      </div>

      <div class="plan-widget__measures">
        <div class="plan-widget__section-heading">
          <span>指标</span>
          <button
            type="button"
            aria-label="新增指标"
            title="新增指标"
            @click="addMeasure(widgetIndex)"
          >
            <Plus :size="15" aria-hidden="true" />
          </button>
        </div>
        <div
          v-for="(measure, measureIndex) in widget.measures"
          :key="`${widget.id}-${measureIndex}`"
          class="plan-widget__measure"
        >
          <input
            v-model="measure.field"
            :data-field="`measure-field-${measureIndex}`"
            aria-label="指标字段"
            @change="commit"
          />
          <select v-model="measure.aggregation" aria-label="聚合方式" @change="commit">
            <option value="sum">sum</option>
            <option value="avg">avg</option>
            <option value="min">min</option>
            <option value="max">max</option>
            <option value="count">count</option>
          </select>
          <button
            type="button"
            :aria-label="`删除指标 ${measure.field}`"
            :title="`删除指标 ${measure.field}`"
            @click="removeMeasure(widgetIndex, measureIndex)"
          >
            <Trash2 :size="15" aria-hidden="true" />
          </button>
        </div>
      </div>
    </article>
  </section>
</template>

<style scoped>
.plan-editor {
  display: grid;
  gap: 12px;
}

.plan-editor__heading,
.plan-widget__heading,
.plan-widget__section-heading,
.plan-widget__measure {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.plan-editor__heading h3,
.plan-editor__heading p {
  margin: 0;
}

.plan-editor__heading p {
  margin-top: 4px;
  color: #5f5e5b;
  font-size: 13px;
}

.plan-widget {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--dp-border);
  border-radius: 6px;
  background: var(--dp-surface);
}

.plan-widget__controls {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.plan-widget__controls label {
  display: grid;
  gap: 4px;
  font-size: 12px;
}

.plan-widget select,
.plan-widget input {
  min-width: 0;
}

.plan-widget__measures {
  display: grid;
  gap: 6px;
}

.plan-widget__measure {
  justify-content: stretch;
}

.plan-widget__measure input {
  flex: 1;
}

.plan-widget button {
  display: inline-grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border: 1px solid var(--dp-border);
  border-radius: 4px;
  background: transparent;
  color: inherit;
}

@media (max-width: 640px) {
  .plan-widget__controls {
    grid-template-columns: 1fr;
  }
}
</style>
