<script setup lang="ts">
import { ArrowLeft, Redo2, Save, Undo2 } from "@lucide/vue";
import { computed, onMounted } from "vue";
import { RouterLink, useRoute } from "vue-router";

import InlineNotice from "../../ui/InlineNotice.vue";
import { useScreenEditorStore } from "./editor/store";

const route = useRoute();
const store = useScreenEditorStore();
const screenId = computed(() => String(route.params.id));

const saveLabel = computed(() => {
  const labels = {
    idle: "尚未加载",
    dirty: "未保存",
    saving: "保存中…",
    saved: "已保存",
    failed: "保存失败",
    conflict: "草稿冲突",
  };
  return labels[store.saveState];
});

onMounted(() => store.load(screenId.value));
</script>

<template>
  <section class="screen-editor-page" aria-label="大屏编辑器">
    <p v-if="store.loading" class="loading-copy" role="status">
      正在加载大屏编辑器…
    </p>
    <InlineNotice v-else-if="store.loadError" tone="error">
      <p>{{ store.loadError.message }}</p>
      <code v-if="store.loadError.requestId">
        {{ store.loadError.requestId }}
      </code>
    </InlineNotice>

    <template v-else-if="store.screen && store.document">
      <header class="editor-toolbar" aria-label="编辑器工具栏">
        <RouterLink
          class="editor-icon-button"
          to="/studio/screens"
          aria-label="返回大屏列表"
        >
          <ArrowLeft :size="16" aria-hidden="true" />
        </RouterLink>
        <div class="editor-title">
          <strong>{{ store.screen.name }}</strong>
          <span :data-state="store.saveState">{{ saveLabel }}</span>
        </div>
        <div class="editor-toolbar__spacer" />
        <button
          class="editor-icon-button"
          type="button"
          aria-label="撤销"
          :disabled="!store.canUndo"
          @click="store.undo"
        >
          <Undo2 :size="16" aria-hidden="true" />
        </button>
        <button
          class="editor-icon-button"
          type="button"
          aria-label="重做"
          :disabled="!store.canRedo"
          @click="store.redo"
        >
          <Redo2 :size="16" aria-hidden="true" />
        </button>
        <button
          class="secondary-button editor-save-button"
          type="button"
          :disabled="store.saveState === 'saving'"
          @click="store.saveNow"
        >
          <Save :size="14" aria-hidden="true" />
          保存
        </button>
      </header>

      <InlineNotice
        v-if="store.saveState === 'conflict'"
        class="editor-conflict"
        tone="error"
      >
        <p>草稿已在其他页面发生变化，请重新载入后继续编辑。</p>
      </InlineNotice>

      <div class="editor-skeleton">
        <aside class="editor-panel editor-panel--left" aria-label="组件与图层">
          <h2>组件</h2>
          <p>组件库与图层将在这里显示。</p>
        </aside>
        <main class="editor-canvas-host" aria-label="大屏画布">
          <div
            class="editor-canvas-placeholder"
            :style="{
              aspectRatio: `${store.document.canvas.width} / ${store.document.canvas.height}`,
            }"
          >
            <span>
              {{ store.document.canvas.width }} ×
              {{ store.document.canvas.height }}
            </span>
          </div>
        </main>
        <aside class="editor-panel editor-panel--right" aria-label="属性面板">
          <h2>属性</h2>
          <p>选择组件后在这里编辑数据、样式与交互。</p>
        </aside>
      </div>
    </template>
  </section>
</template>
