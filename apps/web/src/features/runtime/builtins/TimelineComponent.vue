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
const title = computed(() => stringProp(props.instance.props, "title", "事件流"));
const rows = computed(() => props.result?.rows.slice(0, 8) ?? []);
</script>

<template>
  <section class="screen-timeline">
    <header><strong>{{ title }}</strong><span>{{ rows.length }} 条</span></header>
    <p v-if="error || loading || rows.length === 0" class="screen-component-state">{{ loading ? "正在加载…" : error ? "数据加载失败" : "暂无事件" }}</p>
    <ol v-else>
      <li v-for="(row, index) in rows" :key="index"><i :class="{ 'is-last': index === rows.length - 1 }"></i><span><strong>{{ formatCell(row[1] ?? row[0]) }}</strong><small>{{ formatCell(row[2]) }}</small></span><time>{{ formatCell(row[0]) }}</time></li>
    </ol>
  </section>
</template>

<style scoped>
.screen-timeline { box-sizing: border-box; width: 100%; height: 100%; padding: 14px; overflow: hidden; color: var(--screen-text-primary, #edf7ff); }
.screen-timeline header { display: flex; justify-content: space-between; margin-bottom: 10px; }
.screen-timeline header strong { font-size: 14px; font-weight: 600; }
.screen-timeline header span { color: var(--screen-text-muted, #638198); font-size: 10px; }
.screen-timeline ol { display: grid; gap: 0; margin: 0; padding: 0; list-style: none; }
.screen-timeline li { position: relative; display: grid; grid-template-columns: 15px minmax(0, 1fr) auto; align-items: center; gap: 7px; min-height: 38px; }
.screen-timeline li::before { position: absolute; top: 0; bottom: 0; left: 5px; width: 1px; background: var(--screen-panel-border, #1b4160); content: ""; }
.screen-timeline li:last-child::before { bottom: 50%; }
.screen-timeline li i { z-index: 1; width: 10px; height: 10px; border: 2px solid var(--screen-accent, #26d9c1); border-radius: 50%; background: var(--screen-panel-background, #0b1b2b); }
.screen-timeline li i.is-last { border-color: var(--screen-warning, #f3b638); }
.screen-timeline li span { display: grid; gap: 2px; min-width: 0; }
.screen-timeline li strong { overflow: hidden; font-size: 10px; font-weight: 500; text-overflow: ellipsis; white-space: nowrap; }
.screen-timeline li small, .screen-timeline time { color: var(--screen-text-secondary, #9ab3c8); font-size: 9px; }
.screen-component-state { margin: 0; color: var(--screen-text-secondary, #9ab3c8); font-size: 12px; }
</style>
