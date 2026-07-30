<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";

import InlineNotice from "../../ui/InlineNotice.vue";
import ComponentLibrary from "./editor/ComponentLibrary.vue";
import EditorToolbar from "./editor/EditorToolbar.vue";
import InspectorPanel from "./editor/InspectorPanel.vue";
import LayersPanel from "./editor/LayersPanel.vue";
import ScreenCanvas from "./editor/ScreenCanvas.vue";
import { useScreenEditorStore } from "./editor/store";

const route = useRoute();
const store = useScreenEditorStore();
const screenId = computed(() => String(route.params.id));
const canvas = ref<InstanceType<typeof ScreenCanvas> | null>(null);

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
      <EditorToolbar
        :save-label="saveLabel"
        :zoom="canvas?.zoom ?? 0.5"
        @align="canvas?.alignSelection($event)"
        @zoom="canvas?.setZoom($event)"
      />

      <InlineNotice
        v-if="store.saveState === 'conflict'"
        class="editor-conflict"
        tone="error"
      >
        <p>草稿已在其他页面发生变化，请重新载入后继续编辑。</p>
      </InlineNotice>

      <div class="editor-workspace">
        <aside class="editor-panel editor-panel--left" aria-label="组件与图层">
          <ComponentLibrary />
          <LayersPanel />
        </aside>
        <main class="editor-canvas-region" aria-label="大屏画布">
          <ScreenCanvas ref="canvas" />
        </main>
        <aside class="editor-panel editor-panel--right" aria-label="属性面板">
          <InspectorPanel />
        </aside>
      </div>
    </template>
  </section>
</template>
