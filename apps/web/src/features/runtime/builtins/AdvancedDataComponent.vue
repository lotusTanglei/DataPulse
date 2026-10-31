<script setup lang="ts">
import { computed } from "vue";

import type { JsonValue, QueryResult } from "../../query/types";
import type { ComponentInstance, LoadAsset } from "../types";
import {
  clamp,
  formatCell,
  formatNumber,
  numberProp,
  numericValue,
  stringProp,
} from "./format";

const props = defineProps<{
  instance: ComponentInstance;
  result: QueryResult | null;
  loading: boolean;
  error: unknown | null;
  loadAsset: LoadAsset;
}>();

const title = computed(() => stringProp(props.instance.props, "title"));
const emptyText = computed(() => stringProp(props.instance.props, "empty_text", "暂无数据"));
const rows = computed(() => props.result?.rows ?? []);
const mergeColumns = computed(() => Math.trunc(numberProp(props.instance.props, "merge_columns", 1, { min: 0, max: 4 })));
const threshold = computed(() => numberProp(props.instance.props, "highlight_threshold", 80));

function timestamp(value: JsonValue | undefined): number | null {
  const parsed = Date.parse(String(value ?? ""));
  return Number.isFinite(parsed) ? parsed : null;
}

const ganttRange = computed(() => {
  const times = rows.value.flatMap((row) => [timestamp(row[1]), timestamp(row[2])]).filter(
    (value): value is number => value !== null,
  );
  const start = Math.min(...times);
  const end = Math.max(...times);
  return Number.isFinite(start) && Number.isFinite(end) && end > start
    ? { start, end, span: end - start }
    : null;
});

function ganttStyle(row: QueryResult["rows"][number]): Record<string, string> {
  const range = ganttRange.value;
  const start = timestamp(row[1]);
  const end = timestamp(row[2]);
  if (!range || start === null || end === null) return { left: "0%", width: "8%" };
  const left = clamp(((start - range.start) / range.span) * 100, 0, 100);
  const width = clamp(((Math.max(end, start) - start) / range.span) * 100, 2, 100 - left);
  return { left: `${left}%`, width: `${width}%` };
}

function rowSpan(rowIndex: number, columnIndex: number): number {
  if (columnIndex >= mergeColumns.value) return 1;
  const value = rows.value[rowIndex]?.[columnIndex];
  if (rowIndex > 0 && rows.value[rowIndex - 1]?.[columnIndex] === value) return 0;
  let count = 1;
  while (rows.value[rowIndex + count]?.[columnIndex] === value) count += 1;
  return count;
}

function cellClass(value: JsonValue | undefined): string {
  const numeric = numericValue(value);
  return numeric !== null && numeric >= threshold.value ? "is-highlight" : "";
}

function metricDelta(row: QueryResult["rows"][number]): string {
  const current = numericValue(row[1]);
  const previous = numericValue(row[2]);
  if (current === null || previous === null || previous === 0) return "—";
  const delta = ((current - previous) / Math.abs(previous)) * 100;
  return `${delta >= 0 ? "+" : ""}${formatNumber(delta, 1)}%`;
}

function metricClass(row: QueryResult["rows"][number]): string {
  const current = numericValue(row[1]);
  const previous = numericValue(row[2]);
  if (current === null || previous === null || current === previous) return "is-flat";
  return current > previous ? "is-up" : "is-down";
}
</script>

<template>
  <section class="advanced-data" :data-variant="instance.type">
    <header v-if="title"><strong>{{ title }}</strong><span>{{ rows.length }} 项</span></header>
    <p v-if="error" class="advanced-data__state" role="status">数据加载失败</p>
    <p v-else-if="loading" class="advanced-data__state" role="status">正在加载…</p>
    <p v-else-if="!result || rows.length === 0" class="advanced-data__state" role="status">{{ emptyText }}</p>

    <ol v-else-if="instance.type === 'builtin.steps'" class="steps-list">
      <li v-for="(row, index) in rows" :key="index" :class="String(row[2] ?? '').toLowerCase()">
        <i>{{ index + 1 }}</i><span><strong>{{ formatCell(row[0]) }}</strong><small>{{ formatCell(row[1]) }}</small></span><em>{{ formatCell(row[2]) }}</em>
      </li>
    </ol>

    <div v-else-if="instance.type === 'builtin.gantt'" class="gantt-list">
      <div v-for="(row, index) in rows" :key="index" class="gantt-row">
        <strong :title="formatCell(row[0])">{{ formatCell(row[0]) }}</strong>
        <span class="gantt-track"><i :style="ganttStyle(row)"><b>{{ formatCell(row[3]) }}</b></i></span>
      </div>
    </div>

    <div v-else-if="instance.type === 'builtin.kpi_group'" class="metric-grid">
      <article v-for="(row, index) in rows.slice(0, 8)" :key="index">
        <small>{{ formatCell(row[0]) }}</small><strong>{{ formatCell(row[1]) }}</strong><span>{{ formatCell(row[2]) }}</span>
      </article>
    </div>

    <div v-else-if="instance.type === 'builtin.metric_comparison'" class="metric-grid metric-grid--comparison">
      <article v-for="(row, index) in rows.slice(0, 8)" :key="index">
        <small>{{ formatCell(row[0]) }}</small><strong>{{ formatCell(row[1]) }}</strong><span :class="metricClass(row)">{{ metricDelta(row) }}</span>
      </article>
    </div>

    <div v-else class="rich-table">
      <table>
        <thead><tr><th v-for="column in result.columns" :key="column.name">{{ column.name }}</th></tr></thead>
        <tbody>
          <tr v-for="(row, rowIndex) in rows" :key="rowIndex">
            <template v-for="(column, columnIndex) in result.columns" :key="column.name">
              <td
                v-if="rowSpan(rowIndex, columnIndex) > 0"
                :rowspan="rowSpan(rowIndex, columnIndex)"
                :class="cellClass(row[columnIndex])"
                :title="formatCell(row[columnIndex])"
              >{{ formatCell(row[columnIndex]) }}</td>
            </template>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.advanced-data { box-sizing: border-box; width: 100%; height: 100%; min-height: 0; padding: 14px; overflow: auto; color: var(--screen-text-primary, #eaf4ff); }
.advanced-data header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.advanced-data header strong { font-size: 14px; }
.advanced-data header span, .advanced-data__state { color: var(--screen-text-secondary, #94a3b8); font-size: 11px; }
.advanced-data__state { margin: 0; }
.steps-list { display: grid; gap: 0; margin: 0; padding: 0; list-style: none; }
.steps-list li { position: relative; display: grid; grid-template-columns: 28px minmax(0, 1fr) auto; align-items: center; gap: 10px; min-height: 48px; }
.steps-list li:not(:last-child)::after { position: absolute; top: 34px; bottom: -14px; left: 13px; width: 1px; background: var(--screen-panel-border, #31506a); content: ""; }
.steps-list i { z-index: 1; display: grid; width: 26px; height: 26px; place-items: center; border: 1px solid var(--screen-accent, #26d9c1); border-radius: 50%; background: var(--screen-panel-background, #0b1b2b); color: var(--screen-accent, #26d9c1); font-size: 10px; font-style: normal; }
.steps-list span { display: grid; min-width: 0; }
.steps-list strong { overflow: hidden; font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.steps-list small, .steps-list em { color: var(--screen-text-secondary, #94a3b8); font-size: 9px; font-style: normal; }
.gantt-list { display: grid; gap: 8px; }
.gantt-row { display: grid; grid-template-columns: minmax(80px, 24%) minmax(0, 1fr); align-items: center; gap: 10px; }
.gantt-row > strong { overflow: hidden; font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.gantt-track { position: relative; height: 18px; border-radius: 2px; background: rgb(148 163 184 / 9%); }
.gantt-track i { position: absolute; top: 2px; height: 14px; min-width: 2px; border-radius: 2px; background: linear-gradient(90deg, var(--screen-accent, #26d9c1), var(--screen-info, #4da3ff)); }
.gantt-track b { display: block; padding: 1px 5px; overflow: hidden; color: #06131d; font-size: 8px; text-overflow: ellipsis; white-space: nowrap; }
.metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 8px; }
.metric-grid article { display: grid; min-width: 0; gap: 4px; padding: 12px; border: 1px solid var(--screen-component-border, #24445f); border-radius: 4px; background: rgb(16 37 58 / 58%); }
.metric-grid small { overflow: hidden; color: var(--screen-text-secondary, #94a3b8); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.metric-grid strong { overflow: hidden; font-size: 21px; text-overflow: ellipsis; white-space: nowrap; }
.metric-grid span { color: var(--screen-text-secondary, #94a3b8); font-size: 9px; }
.metric-grid span.is-up { color: var(--screen-success, #43d17d); }
.metric-grid span.is-down { color: var(--screen-danger, #f16d75); }
.rich-table { width: 100%; overflow: auto; }
.rich-table table { width: 100%; border-collapse: collapse; font-size: 11px; }
.rich-table th, .rich-table td { max-width: 260px; padding: 8px 10px; overflow: hidden; border: 1px solid var(--screen-component-border, #24445f); text-align: left; text-overflow: ellipsis; white-space: nowrap; }
.rich-table th { position: sticky; top: 0; background: var(--screen-table-header, #10253a); color: var(--screen-text-secondary, #94a3b8); }
.rich-table td.is-highlight { background: color-mix(in srgb, var(--screen-warning, #f3b638) 16%, transparent); color: var(--screen-warning, #f3b638); font-weight: 600; }
</style>
