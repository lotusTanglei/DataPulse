<script setup lang="ts">
import { defaultComponentRegistry } from "../../runtime/registry";
import { useScreenEditorStore } from "./store";

const store = useScreenEditorStore();

function add(type: string): void {
  const definition = defaultComponentRegistry.get(type);
  if (!definition || !store.document) {
    return;
  }
  const id = crypto.randomUUID();
  store.dispatch({
    type: "add_component",
    component: {
      id,
      type: definition.type,
      frame: {
        x: 40,
        y: 40,
        width: definition.defaultFrame.width,
        height: definition.defaultFrame.height,
        z_index: store.document.components?.length ?? 0,
      },
      props: structuredClone(definition.defaultProps),
      style: {},
      state: { locked: false, hidden: false },
      data_binding: {},
      interactions: [],
    },
  });
  store.selection = [id];
}
</script>

<template>
  <section class="component-library" aria-label="组件库">
    <h2>组件</h2>
    <div class="component-library__grid">
      <button
        v-for="definition in defaultComponentRegistry.list()"
        :key="definition.type"
        type="button"
        @click="add(definition.type)"
      >
        <span>＋</span>
        {{ definition.label }}
      </button>
    </div>
  </section>
</template>
