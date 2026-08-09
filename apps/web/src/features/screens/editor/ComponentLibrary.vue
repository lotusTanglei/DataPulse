<script setup lang="ts">
import { defaultComponentRegistry } from "../../runtime/registry";
import type { ComponentFrame } from "./commands";
import { snapToGrid } from "./geometry";
import { useScreenEditorStore } from "./store";

const store = useScreenEditorStore();

function overlaps(
  candidate: Pick<ComponentFrame, "x" | "y" | "width" | "height">,
  frame: ComponentFrame,
  gap = 20,
): boolean {
  return (
    candidate.x < frame.x + frame.width + gap &&
    candidate.x + candidate.width + gap > frame.x &&
    candidate.y < frame.y + frame.height + gap &&
    candidate.y + candidate.height + gap > frame.y
  );
}

function findPlacement(width: number, height: number): { x: number; y: number } {
  const document = store.document!;
  const maxX = Math.max(0, document.canvas.width - width);
  const maxY = Math.max(0, document.canvas.height - height);
  const center = {
    x: snapToGrid(maxX / 2),
    y: snapToGrid(maxY / 2),
  };
  const candidates = new Map<string, { x: number; y: number }>();
  const addCandidate = (x: number, y: number) => {
    const candidate = {
      x: Math.min(maxX, Math.max(0, snapToGrid(x))),
      y: Math.min(maxY, Math.max(0, snapToGrid(y))),
    };
    candidates.set(`${candidate.x}:${candidate.y}`, candidate);
  };
  addCandidate(center.x, center.y);
  for (let y = 20; y <= maxY; y += 40) {
    for (let x = 20; x <= maxX; x += 40) {
      addCandidate(x, y);
    }
  }
  const ordered = [...candidates.values()].sort(
    (first, second) =>
      (first.x - center.x) ** 2 + (first.y - center.y) ** 2 -
      ((second.x - center.x) ** 2 + (second.y - center.y) ** 2),
  );
  const frames = document.components?.map((component) => component.frame) ?? [];
  const available = ordered.find((position) =>
    frames.every((frame) =>
      !overlaps({ ...position, width, height }, frame),
    ),
  );
  if (available) {
    return available;
  }
  const index = document.components?.length ?? 0;
  return {
    x: Math.min(maxX, Math.max(0, center.x + ((index % 5) - 2) * 40)),
    y: Math.min(maxY, Math.max(0, center.y + (Math.floor(index / 5) % 5 - 2) * 40)),
  };
}

function add(type: string): void {
  const definition = defaultComponentRegistry.get(type);
  if (!definition || !store.document) {
    return;
  }
  const id = crypto.randomUUID();
  const placement = findPlacement(
    definition.defaultFrame.width,
    definition.defaultFrame.height,
  );
  store.dispatch({
    type: "add_component",
    component: {
      id,
      type: definition.type,
      frame: {
        x: placement.x,
        y: placement.y,
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
