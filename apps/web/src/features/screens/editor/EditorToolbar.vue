<script setup lang="ts">
import {
  AlignCenter,
  AlignLeft,
  ArrowLeft,
  Redo2,
  Save,
  Undo2,
  ZoomIn,
  ZoomOut,
} from "@lucide/vue";
import { RouterLink } from "vue-router";

import { useScreenEditorStore } from "./store";

defineProps<{ saveLabel: string; zoom: number }>();
const emit = defineEmits<{
  align: [alignment: "left" | "center"];
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
    <button class="editor-icon-button" type="button" aria-label="左对齐" @click="emit('align', 'left')">
      <AlignLeft :size="15" />
    </button>
    <button class="editor-icon-button" type="button" aria-label="水平居中" @click="emit('align', 'center')">
      <AlignCenter :size="15" />
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
    <button class="secondary-button editor-save-button" type="button" :disabled="store.saveState === 'saving'" @click="store.saveNow">
      <Save :size="14" />
      保存
    </button>
  </header>
</template>
