<script setup lang="ts">
import { computed } from "vue";

import type { QueryResult } from "../../query/types";
import type { ComponentInstance, LoadAsset } from "../types";
import { formatCell, stringProp } from "./format";

const props = defineProps<{
  instance: ComponentInstance;
  result: QueryResult | null;
  loading: boolean;
  error: unknown | null;
  loadAsset: LoadAsset;
}>();

const title = computed(() => stringProp(props.instance.props, "title", "实时告警"));
const rows = computed(() => props.result?.rows.slice(0, 8) ?? []);
const levelClass = (value: unknown): string => {
  const level = String(value ?? "low").toLowerCase();
  return level === "high" || level === "critical" ? "is-danger" : level === "medium" || level === "warning" ? "is-warning" : "is-info";
};
</script>

<template>
  <section class="screen-alert-list">
    <header><strong>{{ title }}</strong><span>{{ rows.length }} 项</span></header>
    <p v-if="error || loading || rows.length === 0" class="screen-component-state">{{ loading ? "正在加载…" : error ? "数据加载失败" : "暂无告警" }}</p>
    <ul v-else>
      <li v-for="(row, index) in rows" :key="index">
        <i :class="levelClass(row[0])" aria-hidden="true"></i>
        <span><strong>{{ formatCell(row[1]) }}</strong><small>{{ formatCell(row[2]) }}</small></span>
        <time>{{ formatCell(row[3]) }}</time>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.screen-alert-list { box-sizing: border-box; width: 100%; height: 100%; padding: 14px; overflow: hidden; color: var(--screen-text-primary, #edf7ff); }
.screen-alert-list header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 9px; }
.screen-alert-list header strong { font-size: 14px; font-weight: 600; }
.screen-alert-list header span { color: var(--screen-warning, #f3b638); font-size: 10px; }
.screen-alert-list ul { display: grid; gap: 0; margin: 0; padding: 0; list-style: none; }
.screen-alert-list li { display: grid; grid-template-columns: 7px minmax(0, 1fr) auto; align-items: center; gap: 9px; min-height: 42px; border-bottom: 1px solid var(--screen-panel-border, #1b4160); }
.screen-alert-list li:last-child { border-bottom: 0; }
.screen-alert-list li > i { width: 6px; height: 6px; border-radius: 50%; box-shadow: 0 0 7px currentColor; }
.screen-alert-list li > i.is-danger { color: var(--screen-danger, #f16d75); background: currentColor; }
.screen-alert-list li > i.is-warning { color: var(--screen-warning, #f3b638); background: currentColor; }
.screen-alert-list li > i.is-info { color: var(--screen-info, #3b8df4); background: currentColor; }
.screen-alert-list li > span { display: grid; gap: 3px; min-width: 0; }
.screen-alert-list li strong { overflow: hidden; font-size: 11px; font-weight: 500; text-overflow: ellipsis; white-space: nowrap; }
.screen-alert-list li small, .screen-alert-list time { overflow: hidden; color: var(--screen-text-secondary, #9ab3c8); font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }
.screen-component-state { margin: 0; color: var(--screen-text-secondary, #9ab3c8); font-size: 12px; }
</style>
