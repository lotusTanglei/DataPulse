<script setup lang="ts">
import { computed } from "vue";

import type { QueryResult } from "../../query/types";
import type { ComponentInstance, LoadAsset } from "../types";
import { formatCell, numberProp, stringProp } from "./format";

const props = defineProps<{
  instance: ComponentInstance;
  result: QueryResult | null;
  loading: boolean;
  error: unknown | null;
  loadAsset: LoadAsset;
}>();

const emptyText = computed(() =>
  stringProp(props.instance.props, "empty_text", "暂无数据"),
);
const maxRows = computed(() =>
  numberProp(props.instance.props, "max_rows", 100, { min: 1, max: 1000 }),
);
const rows = computed(() => props.result?.rows.slice(0, maxRows.value) ?? []);
</script>

<template>
  <div class="screen-table">
    <p v-if="error" class="screen-component-state" role="status">
      数据加载失败
    </p>
    <p v-else-if="loading" class="screen-component-state" role="status">
      正在加载…
    </p>
    <p
      v-else-if="!result || rows.length === 0"
      class="screen-component-state"
      role="status"
    >
      {{ emptyText }}
    </p>
    <div v-else class="screen-table__scroll">
      <table>
        <thead>
          <tr>
            <th
              v-for="(column, columnIndex) in result.columns"
              :key="`${columnIndex}:${column.name}`"
              scope="col"
            >
              {{ column.name }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, rowIndex) in rows" :key="rowIndex">
            <td
              v-for="(column, columnIndex) in result.columns"
              :key="`${columnIndex}:${column.name}`"
              :title="formatCell(row[columnIndex])"
            >
              {{ formatCell(row[columnIndex]) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.screen-table {
  box-sizing: border-box;
  display: grid;
  width: 100%;
  height: 100%;
  min-height: 0;
  place-items: center;
  border: 1px solid var(--screen-component-border, transparent);
  border-radius: var(--screen-component-radius, 8px);
  background: var(--screen-component-surface, transparent);
  color: var(--screen-text-primary, #f8fafc);
}

.screen-table__scroll {
  width: 100%;
  height: 100%;
  overflow: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  text-align: left;
}

th,
td {
  max-width: 320px;
  padding: 10px 12px;
  overflow: hidden;
  border-bottom: 1px solid var(--screen-component-border, transparent);
  text-overflow: ellipsis;
  white-space: nowrap;
}

th {
  position: sticky;
  top: 0;
  background: var(--screen-table-header, var(--screen-component-surface));
  color: var(--screen-text-secondary, #94a3b8);
  font-weight: 600;
}

tbody tr {
  transition: background 120ms ease;
}

tbody tr:nth-child(even) {
  background: rgb(148 163 184 / 4%);
}

tbody tr:hover {
  background: color-mix(in srgb, var(--screen-accent, #3b82f6) 8%, transparent);
}

.screen-component-state {
  margin: 0;
  color: var(--screen-text-secondary, #94a3b8);
  font-size: 13px;
}
</style>
