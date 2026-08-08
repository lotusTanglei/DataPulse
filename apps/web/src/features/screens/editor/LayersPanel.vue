<script setup lang="ts">
import { Eye, EyeOff, Lock, Unlock } from "@lucide/vue";
import { computed } from "vue";

import { defaultComponentRegistry } from "../../runtime/registry";
import { useScreenEditorStore } from "./store";

const store = useScreenEditorStore();
const layers = computed(() =>
  [...(store.document?.components ?? [])].sort(
    (first, second) =>
      (second.frame.z_index ?? 0) - (first.frame.z_index ?? 0),
  ),
);

function select(id: string): void {
  const component = store.document?.components?.find((item) => item.id === id);
  const groupId = component?.state?.group_id;
  store.selection = groupId
    ? (store.document?.components ?? [])
        .filter((item) => item.state?.group_id === groupId)
        .map((item) => item.id)
    : [id];
}

function toggleHidden(id: string, hidden: boolean): void {
  store.dispatch({
    type: "set_component_state",
    component_ids: [id],
    patch: { hidden: !hidden },
  });
}

function toggleLocked(id: string, locked: boolean): void {
  store.dispatch({
    type: "set_component_state",
    component_ids: [id],
    patch: { locked: !locked },
  });
}

function moveLayer(id: string, direction: "front" | "back"): void {
  const ids = (store.document?.components ?? []).map(
    (component) => component.id,
  );
  if (!ids.includes(id)) {
    return;
  }
  const remaining = ids.filter((componentId) => componentId !== id);
  store.dispatch({
    type: "reorder_components",
    component_ids:
      direction === "front" ? [...remaining, id] : [id, ...remaining],
  });
}

defineExpose({ moveLayer });
</script>

<template>
  <section class="layers-panel" aria-label="图层">
    <h2>图层</h2>
    <p v-if="layers.length === 0" class="editor-panel-empty">暂无组件</p>
    <div
      v-for="layer in layers"
      :key="layer.id"
      class="layer-row"
      :class="{ 'is-selected': store.selection.includes(layer.id) }"
      :data-layer-id="layer.id"
      role="button"
      tabindex="0"
      @click="select(layer.id)"
      @keydown.enter="select(layer.id)"
    >
      <span>
        <small v-if="layer.state?.group_id" class="layer-group-badge">组</small>
        {{ defaultComponentRegistry.get(layer.type)?.label ?? layer.type }}
      </span>
      <button
        type="button"
        aria-label="移到最底层"
        @click.stop="moveLayer(layer.id, 'back')"
      >
        ↓
      </button>
      <button
        type="button"
        aria-label="移到最顶层"
        @click.stop="moveLayer(layer.id, 'front')"
      >
        ↑
      </button>
      <button
        type="button"
        :aria-label="layer.state?.hidden ? '显示图层' : '隐藏图层'"
        @click.stop="toggleHidden(layer.id, layer.state?.hidden ?? false)"
      >
        <EyeOff v-if="layer.state?.hidden" :size="13" />
        <Eye v-else :size="13" />
      </button>
      <button
        type="button"
        :aria-label="layer.state?.locked ? '解锁图层' : '锁定图层'"
        @click.stop="toggleLocked(layer.id, layer.state?.locked ?? false)"
      >
        <Lock v-if="layer.state?.locked" :size="13" />
        <Unlock v-else :size="13" />
      </button>
    </div>
  </section>
</template>
