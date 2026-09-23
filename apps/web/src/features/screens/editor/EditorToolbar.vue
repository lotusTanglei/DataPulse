<script setup lang="ts">
import {
  AlignCenter,
  AlignCenterHorizontal,
  AlignCenterVertical,
  AlignLeft,
  AlignRight,
  ArrowLeft,
  Eye,
  Grid3X3,
  Magnet,
  Redo2,
  RefreshCw,
  Save,
  Send,
  Space,
  Undo2,
  ZoomIn,
  ZoomOut,
} from "@lucide/vue";
import { RouterLink } from "vue-router";

import { useScreenEditorStore } from "./store";

  withDefaults(
  defineProps<{
    publishing?: boolean;
    canPublish?: boolean;
    saveLabel: string;
    zoom: number;
    showGrid?: boolean;
    snapEnabled?: boolean;
    selectionCount?: number;
    canUngroup?: boolean;
  }>(),
  { publishing: false, canPublish: false, showGrid: true, snapEnabled: true, selectionCount: 0, canUngroup: false },
);
const emit = defineEmits<{
  align: [alignment: "left" | "center" | "right" | "top" | "middle" | "bottom"];
  distribute: [axis: "horizontal" | "vertical"];
  toggleGrid: [];
  toggleSnap: [];
  group: [];
  ungroup: [];
  publish: [];
  refresh: [];
  zoom: [value: number];
}>();
const store = useScreenEditorStore();
</script>

<template>
  <header class="editor-toolbar" aria-label="编辑器工具栏">
    <RouterLink class="editor-icon-button" to="/studio/screens" aria-label="返回大屏列表">
      <ArrowLeft :size="16" />
    </RouterLink>
    <div class="editor-title">
      <strong>{{ store.screen?.name }}</strong>
      <span :data-state="store.saveState">{{ saveLabel }}</span>
    </div>
    <div class="editor-toolbar__spacer" />
    <button class="editor-icon-button" type="button" aria-label="左对齐" :disabled="selectionCount < 2" @click="emit('align', 'left')">
      <AlignLeft :size="15" />
    </button>
    <button class="editor-icon-button" type="button" aria-label="水平居中" :disabled="selectionCount < 2" @click="emit('align', 'center')">
      <AlignCenter :size="15" />
    </button>
    <button class="editor-icon-button" type="button" aria-label="右对齐" :disabled="selectionCount < 2" @click="emit('align', 'right')">
      <AlignRight :size="15" />
    </button>
    <button
      class="editor-icon-button editor-text-tool"
      type="button"
      aria-label="组合"
      :disabled="selectionCount < 2"
      @click="emit('group')"
    >
      组合
    </button>
    <button
      class="editor-icon-button editor-text-tool"
      type="button"
      aria-label="取消组合"
      :disabled="!canUngroup"
      @click="emit('ungroup')"
    >
      取消组合
    </button>
    <button class="editor-icon-button" type="button" aria-label="顶部对齐" :disabled="selectionCount < 2" @click="emit('align', 'top')">
      <AlignCenterHorizontal :size="15" />
    </button>
    <button class="editor-icon-button" type="button" aria-label="垂直居中" :disabled="selectionCount < 2" @click="emit('align', 'middle')">
      <AlignCenterVertical :size="15" />
    </button>
    <button class="editor-icon-button" type="button" aria-label="底部对齐" :disabled="selectionCount < 2" @click="emit('align', 'bottom')">
      <AlignCenterHorizontal :size="15" />
    </button>
    <button
      class="editor-icon-button"
      type="button"
      aria-label="水平等间距"
      :disabled="selectionCount < 3"
      @click="emit('distribute', 'horizontal')"
    >
      <Space :size="15" />
    </button>
    <button
      class="editor-icon-button"
      type="button"
      aria-label="垂直等间距"
      :disabled="selectionCount < 3"
      @click="emit('distribute', 'vertical')"
    >
      <Space :size="15" />
    </button>
    <button
      class="editor-icon-button"
      type="button"
      aria-label="网格"
      :class="{ 'is-active': showGrid }"
      @click="emit('toggleGrid')"
    >
      <Grid3X3 :size="15" />
    </button>
    <button
      class="editor-icon-button"
      type="button"
      aria-label="吸附"
      :class="{ 'is-active': snapEnabled }"
      @click="emit('toggleSnap')"
    >
      <Magnet :size="15" />
    </button>
    <button class="editor-icon-button" type="button" aria-label="缩小" @click="emit('zoom', zoom - 0.1)">
      <ZoomOut :size="15" />
    </button>
    <span class="editor-zoom-label">{{ Math.round(zoom * 100) }}%</span>
    <button class="editor-icon-button" type="button" aria-label="放大" @click="emit('zoom', zoom + 0.1)">
      <ZoomIn :size="15" />
    </button>
    <button class="editor-icon-button" type="button" aria-label="撤销" :disabled="!store.canUndo" @click="store.undo">
      <Undo2 :size="16" />
    </button>
    <button class="editor-icon-button" type="button" aria-label="重做" :disabled="!store.canRedo" @click="store.redo">
      <Redo2 :size="16" />
    </button>
    <button class="editor-icon-button" type="button" aria-label="刷新数据" title="重新查询画布数据" @click="emit('refresh')">
      <RefreshCw :size="16" />
    </button>
    <RouterLink
      class="secondary-button editor-save-button"
      data-action="preview-screen"
      :to="{ name: 'screen-preview', params: { id: store.screen?.id } }"
      target="_blank"
    >
      <Eye :size="14" />
      预览
    </RouterLink>
    <button class="secondary-button editor-save-button" type="button" :disabled="store.saveState === 'saving'" @click="store.saveNow">
      <Save :size="14" />
      保存
    </button>
    <button
      class="primary-button editor-save-button"
      data-action="publish-screen"
      type="button"
      :disabled="!canPublish || publishing || store.saveState === 'saving' || store.saveState === 'conflict'"
      @click="emit('publish')"
    >
      <Send :size="14" />
      {{ publishing ? "发布中…" : "发布" }}
    </button>
  </header>
</template>
