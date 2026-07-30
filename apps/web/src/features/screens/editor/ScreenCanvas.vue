<script setup lang="ts">
import Moveable from "moveable";
import Selecto from "selecto";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

import ComponentHost from "../../runtime/ComponentHost.vue";
import { defaultComponentRegistry } from "../../runtime/registry";
import type { ComponentInstance } from "./commands";
import { snapToGrid, translateFrame } from "./geometry";
import { useScreenEditorStore } from "./store";

type Alignment = "left" | "center" | "right" | "top" | "middle" | "bottom";

const props = withDefaults(
  defineProps<{
    idFactory?: () => string;
  }>(),
  {
    idFactory: () => crypto.randomUUID(),
  },
);

const store = useScreenEditorStore();
const host = ref<HTMLElement | null>(null);
const canvas = ref<HTMLElement | null>(null);
const zoom = ref(0.5);
let clipboard: string[] = [];
let selecto: Selecto | null = null;
let moveable: Moveable | null = null;

const visibleComponents = computed(() =>
  (store.document?.components ?? []).filter(
    (component) => !component.state?.hidden,
  ),
);
const selectedComponents = computed(() => {
  const selected = new Set(store.selection);
  return (store.document?.components ?? []).filter((component) =>
    selected.has(component.id),
  );
});
const selectionBounds = computed(() => {
  if (selectedComponents.value.length === 0) {
    return null;
  }
  const left = Math.min(
    ...selectedComponents.value.map((component) => component.frame.x),
  );
  const top = Math.min(
    ...selectedComponents.value.map((component) => component.frame.y),
  );
  const right = Math.max(
    ...selectedComponents.value.map(
      (component) => component.frame.x + component.frame.width,
    ),
  );
  const bottom = Math.max(
    ...selectedComponents.value.map(
      (component) => component.frame.y + component.frame.height,
    ),
  );
  return { x: left, y: top, width: right - left, height: bottom - top };
});
const canvasStyle = computed(() => ({
  width: `${store.document?.canvas.width ?? 1920}px`,
  height: `${store.document?.canvas.height ?? 1080}px`,
  backgroundColor:
    typeof store.document?.canvas.background?.color === "string"
      ? store.document.canvas.background.color
      : "#0b1020",
  transform: `scale(${zoom.value})`,
}));
const stageStyle = computed(() => ({
  width: `${(store.document?.canvas.width ?? 1920) * zoom.value}px`,
  height: `${(store.document?.canvas.height ?? 1080) * zoom.value}px`,
}));

function componentById(id: string): ComponentInstance | undefined {
  return store.document?.components?.find((component) => component.id === id);
}

function editable(ids: string[]): ComponentInstance[] {
  const selected = new Set(ids);
  return (store.document?.components ?? []).filter(
    (component) =>
      selected.has(component.id) && !component.state?.locked,
  );
}

function commitDrag(
  ids: string[],
  delta: { dx: number; dy: number },
): void {
  if (!store.document) {
    return;
  }
  const patches = Object.fromEntries(
    editable(ids).map((component) => {
      const translated = translateFrame(
        component.frame,
        { x: delta.dx, y: delta.dy },
        store.document!.canvas,
      );
      return [
        component.id,
        {
          x: snapToGrid(translated.x),
          y: snapToGrid(translated.y),
        },
      ];
    }),
  );
  if (Object.keys(patches).length > 0) {
    store.dispatch({ type: "update_frames", patches });
  }
}

function commitResize(id: string, width: number, height: number): void {
  const component = componentById(id);
  if (!component || component.state?.locked) {
    return;
  }
  store.dispatch({
    type: "update_frames",
    patches: {
      [id]: {
        width: Math.max(40, snapToGrid(width)),
        height: Math.max(40, snapToGrid(height)),
      },
    },
  });
}

function alignSelection(alignment: Alignment): void {
  const components = editable(store.selection);
  if (components.length < 2 || !selectionBounds.value) {
    return;
  }
  const bounds = selectionBounds.value;
  const patches = Object.fromEntries(
    components.map((component) => {
      const patch =
        alignment === "left"
          ? { x: bounds.x }
          : alignment === "center"
            ? { x: bounds.x + (bounds.width - component.frame.width) / 2 }
            : alignment === "right"
              ? { x: bounds.x + bounds.width - component.frame.width }
              : alignment === "top"
                ? { y: bounds.y }
                : alignment === "middle"
                  ? {
                      y:
                        bounds.y +
                        (bounds.height - component.frame.height) / 2,
                    }
                  : {
                      y: bounds.y + bounds.height - component.frame.height,
                    };
      return [component.id, patch];
    }),
  );
  store.dispatch({ type: "update_frames", patches });
}

function copySelection(): void {
  clipboard = editable(store.selection).map((component) => component.id);
}

function pasteSelection(): void {
  if (clipboard.length === 0) {
    return;
  }
  const idMap = Object.fromEntries(
    clipboard.map((sourceId) => [sourceId, props.idFactory()]),
  );
  store.dispatch({
    type: "duplicate_components",
    source_ids: clipboard,
    id_map: idMap,
  });
  store.selection = clipboard.map((sourceId) => idMap[sourceId]!);
}

function removeSelection(): void {
  const ids = editable(store.selection).map((component) => component.id);
  if (ids.length > 0) {
    store.dispatch({ type: "remove_components", component_ids: ids });
    store.selection = [];
  }
}

function setZoom(value: number): void {
  zoom.value = Math.min(2, Math.max(0.1, value));
}

function fitToViewport(width: number, height: number): void {
  if (!store.document) {
    return;
  }
  setZoom(
    Math.min(
      width / store.document.canvas.width,
      height / store.document.canvas.height,
    ),
  );
}

function selectComponent(id: string, event: MouseEvent): void {
  if (event.metaKey || event.ctrlKey || event.shiftKey) {
    store.selection = store.selection.includes(id)
      ? store.selection.filter((selectedId) => selectedId !== id)
      : [...store.selection, id];
  } else {
    store.selection = [id];
  }
}

function keyboard(event: KeyboardEvent): void {
  const modifier = event.metaKey || event.ctrlKey;
  if (modifier && event.key.toLowerCase() === "z") {
    event.preventDefault();
    event.shiftKey ? store.redo() : store.undo();
  } else if (modifier && event.key.toLowerCase() === "c") {
    event.preventDefault();
    copySelection();
  } else if (modifier && event.key.toLowerCase() === "v") {
    event.preventDefault();
    pasteSelection();
  } else if (
    event.key === "Delete" ||
    (event.key === "Backspace" &&
      !(event.target instanceof HTMLInputElement) &&
      !(event.target instanceof HTMLTextAreaElement))
  ) {
    event.preventDefault();
    removeSelection();
  }
}

async function updateMoveableTargets(): Promise<void> {
  await nextTick();
  if (!moveable || !canvas.value) {
    return;
  }
  moveable.target = store.selection
    .map((id) =>
      canvas.value?.querySelector<HTMLElement>(
        `[data-canvas-component="${CSS.escape(id)}"]`,
      ),
    )
    .filter((element): element is HTMLElement => Boolean(element));
  moveable.updateRect();
}

onMounted(() => {
  window.addEventListener("keydown", keyboard);
  if (host.value && canvas.value) {
    selecto = new Selecto({
      container: host.value,
      dragContainer: host.value,
      selectableTargets: [".editor-canvas-component"],
      selectByClick: false,
      selectFromInside: false,
      toggleContinueSelect: ["shift"],
    });
    selecto.on("selectEnd", (event) => {
      store.selection = event.selected
        .map((element) => element.getAttribute("data-canvas-component"))
        .filter((id): id is string => Boolean(id));
    });
    moveable = new Moveable(host.value, {
      target: [],
      draggable: true,
      resizable: true,
      origin: false,
      snappable: true,
      snapGridWidth: 10,
      snapGridHeight: 10,
    });
    moveable.on("dragEnd", (event) => {
      const id = event.target.getAttribute("data-canvas-component");
      const delta = event.lastEvent?.beforeTranslate;
      if (id && delta) {
        commitDrag([id], { dx: delta[0], dy: delta[1] });
      }
    });
    moveable.on("resizeEnd", (event) => {
      const id = event.target.getAttribute("data-canvas-component");
      if (id && event.lastEvent) {
        commitResize(id, event.lastEvent.width, event.lastEvent.height);
      }
    });
    void updateMoveableTargets();
  }
});

watch(() => store.selection, () => void updateMoveableTargets(), {
  deep: true,
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", keyboard);
  selecto?.destroy();
  moveable?.destroy();
});

async function loadAsset(assetId: string, signal?: AbortSignal): Promise<string> {
  const response = await fetch(
    `/api/admin/assets/${encodeURIComponent(assetId)}`,
    { signal },
  );
  if (!response.ok) {
    throw new Error("Asset unavailable.");
  }
  return URL.createObjectURL(await response.blob());
}

defineExpose({
  alignSelection,
  commitDrag,
  commitResize,
  copySelection,
  fitToViewport,
  pasteSelection,
  selectionBounds,
  setZoom,
  zoom,
});
</script>

<template>
  <div ref="host" class="screen-canvas-host">
    <div class="screen-canvas-stage" :style="stageStyle">
      <div ref="canvas" class="screen-canvas" :style="canvasStyle">
        <button
          v-for="component in visibleComponents"
          :key="component.id"
          class="editor-canvas-component"
          :class="{
            'is-selected': store.selection.includes(component.id),
            'is-locked': component.state?.locked,
          }"
          type="button"
          :data-canvas-component="component.id"
          :style="{
            left: `${component.frame.x}px`,
            top: `${component.frame.y}px`,
            width: `${component.frame.width}px`,
            height: `${component.frame.height}px`,
            zIndex: component.frame.z_index ?? 0,
          }"
          @click.stop="selectComponent(component.id, $event)"
        >
          <ComponentHost
            :definition="defaultComponentRegistry.get(component.type)"
            :instance="component"
            :load-asset="loadAsset"
            :query-state="{ status: 'idle', result: null, error: null }"
            :theme="store.document?.theme?.tokens ?? {}"
          />
        </button>
      </div>
    </div>
  </div>
</template>
