<script setup lang="ts">
import { computed } from "vue";

import type { QueryResult } from "../../query/types";
import type { ComponentInstance, LoadAsset } from "../types";
import { formatCell, formatNumber, numericValue, stringProp } from "./format";

const props = defineProps<{
  instance: ComponentInstance;
  result: QueryResult | null;
  loading: boolean;
  error: unknown | null;
  loadAsset: LoadAsset;
}>();

const title = computed(() => stringProp(props.instance.props, "title", "排行榜"));
const rows = computed(() => props.result?.rows.slice(0, 10) ?? []);
function value(row: (typeof rows.value)[number]): number | null { return numericValue(row[1]); }
function maximum(): number { return Math.max(1, ...rows.value.map((row) => value(row) ?? 0)); }
function width(row: (typeof rows.value)[number]): string { return `${Math.max(4, ((value(row) ?? 0) / maximum()) * 100)}%`; }
</script>

<template>
  <section class="screen-ranking">
    <header><strong>{{ title }}</strong><span>{{ rows.length }} 项</span></header>
    <p v-if="error || loading || rows.length === 0" class="screen-component-state">{{ loading ? "正在加载…" : error ? "数据加载失败" : "暂无数据" }}</p>
    <ol v-else>
      <li v-for="(row, index) in rows" :key="index">
        <b :class="{ 'is-top': index < 3 }">{{ String(index + 1).padStart(2, "0") }}</b>
        <span>{{ formatCell(row[0]) }}</span>
        <i><em :style="{ width: width(row) }"></em></i>
        <strong>{{ formatNumber(value(row) ?? 0, 0) }}</strong>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.screen-ranking { box-sizing: border-box; width: 100%; height: 100%; padding: 14px; overflow: hidden; color: var(--screen-text-primary, #edf7ff); }
.screen-ranking header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 15px; }
.screen-ranking header strong { font-size: 14px; font-weight: 600; }
.screen-ranking header span { color: var(--screen-text-muted, #638198); font-size: 10px; }
.screen-ranking ol { display: grid; gap: 13px; margin: 0; padding: 0; list-style: none; }
.screen-ranking li { display: grid; grid-template-columns: 24px minmax(48px, 0.5fr) minmax(48px, 1fr) auto; align-items: center; gap: 8px; font-size: 11px; }
.screen-ranking li > b { color: var(--screen-text-muted, #638198); font-size: 10px; font-weight: 500; }
.screen-ranking li > b.is-top { color: var(--screen-accent, #26d9c1); }
.screen-ranking li > span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.screen-ranking li > i { display: block; height: 5px; overflow: hidden; border-radius: 3px; background: var(--screen-panel-background-alt, #173149); }
.screen-ranking li > i em { display: block; height: 100%; border-radius: inherit; background: var(--screen-accent, #26d9c1); box-shadow: 0 0 8px rgb(38 217 193 / 35%); }
.screen-ranking li > strong { font-variant-numeric: tabular-nums; font-weight: 500; }
.screen-component-state { margin: 0; color: var(--screen-text-secondary, #9ab3c8); font-size: 12px; }
</style>
