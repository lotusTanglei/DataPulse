<script setup lang="ts">
import { AlertTriangle } from "@lucide/vue";
import { useVirtualizer } from "@tanstack/vue-virtual";
import { computed, ref } from "vue";

import type { JsonValue, QueryResult } from "./types";

const props = defineProps<{ result: QueryResult }>();

const scrollElement = ref<HTMLElement | null>(null);
const columnWidth = 180;
const rowHeight = 34;
const tableWidth = computed(() =>
  Math.max(720, props.result.columns.length * columnWidth),
);
const virtualizer = useVirtualizer(
  computed(() => ({
    count: props.result.rows.length,
    getScrollElement: () => scrollElement.value,
    estimateSize: () => rowHeight,
    overscan: 8,
    initialRect: { width: 960, height: 340 },
  })),
);
const virtualRows = computed(() => virtualizer.value.getVirtualItems());
const totalHeight = computed(() => virtualizer.value.getTotalSize());

function formatValue(value: JsonValue | undefined): string {
  if (value === null || value === undefined) {
    return "—";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}
</script>

<template>
  <section class="query-result" aria-label="查询结果">
    <div v-if="result.truncated" class="result-warning" data-truncated-warning>
      <AlertTriangle :size="15" aria-hidden="true" />
      结果已截断，仅返回前 {{ result.row_count.toLocaleString("zh-CN") }} 行。
    </div>
    <div
      ref="scrollElement"
      class="query-result-scroll"
      data-result-scroll
      role="table"
      :aria-rowcount="result.rows.length + 1"
      :aria-colcount="result.columns.length"
    >
      <div
        class="query-result-header"
        role="row"
        :style="{ width: `${tableWidth}px` }"
      >
        <div
          v-for="(column, index) in result.columns"
          :key="index"
          class="query-result-cell query-result-cell--header"
          role="columnheader"
          :data-column-index="index"
          :style="{ width: `${columnWidth}px` }"
          :title="`${column.name} · ${column.data_type}`"
        >
          <strong>{{ column.name }}</strong>
          <span>{{ column.data_type }}</span>
        </div>
      </div>
      <div
        class="query-result-body"
        :style="{ width: `${tableWidth}px`, height: `${totalHeight}px` }"
      >
        <div
          v-for="virtualRow in virtualRows"
          :key="String(virtualRow.key)"
          class="query-result-row"
          data-result-row
          role="row"
          :style="{
            width: `${tableWidth}px`,
            height: `${virtualRow.size}px`,
            transform: `translateY(${virtualRow.start}px)`,
          }"
        >
          <div
            v-for="(column, columnIndex) in result.columns"
            :key="columnIndex"
            class="query-result-cell"
            role="cell"
            :data-column-index="columnIndex"
            :style="{ width: `${columnWidth}px` }"
            :title="formatValue(result.rows[virtualRow.index]?.[columnIndex])"
          >
            {{ formatValue(result.rows[virtualRow.index]?.[columnIndex]) }}
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
