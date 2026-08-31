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
const title = computed(() => stringProp(props.instance.props, "title", "运行状态"));
const rows = computed(() => props.result?.rows.slice(0, 12) ?? []);
const stateClass = (value: unknown): string => {
  const text = String(value ?? "").toLowerCase();
  return text.includes("故障") || text.includes("异常") || text.includes("error") ? "is-danger" : text.includes("暂停") || text.includes("关注") || text.includes("warning") ? "is-warning" : "is-success";
};
</script>

<template>
  <section class="screen-status-matrix">
    <header><strong>{{ title }}</strong><span>状态</span></header>
    <p v-if="error || loading || rows.length === 0" class="screen-component-state">{{ loading ? "正在加载…" : error ? "数据加载失败" : "暂无数据" }}</p>
    <ul v-else>
      <li v-for="(row, index) in rows" :key="index"><i :class="stateClass(row[1])"></i><span>{{ formatCell(row[0]) }}</span><strong>{{ formatCell(row[1]) }}</strong></li>
    </ul>
  </section>
</template>

<style scoped>
.screen-status-matrix { box-sizing: border-box; width: 100%; height: 100%; padding: 14px; overflow: hidden; color: var(--screen-text-primary, #edf7ff); }
.screen-status-matrix header { display: flex; justify-content: space-between; margin-bottom: 11px; }
.screen-status-matrix header strong { font-size: 14px; font-weight: 600; }
.screen-status-matrix header span { color: var(--screen-text-muted, #638198); font-size: 10px; }
.screen-status-matrix ul { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 7px; margin: 0; padding: 0; list-style: none; }
.screen-status-matrix li { display: grid; grid-template-columns: 7px minmax(0, 1fr); gap: 7px; min-width: 0; padding: 8px; background: rgb(16 37 58 / 70%); }
.screen-status-matrix li i { width: 6px; height: 6px; margin-top: 4px; border-radius: 50%; box-shadow: 0 0 7px currentColor; }
.screen-status-matrix li i.is-success { color: var(--screen-success, #43d17d); background: currentColor; }
.screen-status-matrix li i.is-warning { color: var(--screen-warning, #f3b638); background: currentColor; }
.screen-status-matrix li i.is-danger { color: var(--screen-danger, #f16d75); background: currentColor; }
.screen-status-matrix li span, .screen-status-matrix li strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.screen-status-matrix li span { font-size: 10px; }
.screen-status-matrix li strong { grid-column: 2; color: var(--screen-text-secondary, #9ab3c8); font-size: 9px; font-weight: 400; }
.screen-component-state { margin: 0; color: var(--screen-text-secondary, #9ab3c8); font-size: 12px; }
</style>
