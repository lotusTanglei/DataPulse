<script setup lang="ts">
import Moveable from "moveable";
import Selecto from "selecto";
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  toRaw,
  watch,
} from "vue";

import ComponentHost from "../../runtime/ComponentHost.vue";
import { createDataRuntime } from "../../runtime/dataRuntime";
import { useEditorRegistry } from "../../ecosystem/editorPlugins";
import { resolveThemeTokens } from "../../runtime/theme";
import { queryScreenDocument } from "../api";
import type { ComponentInstance } from "./commands";
import {
  alignFrames,
  distributeFrames,
  selectionBounds as getSelectionBounds,
  snapFrame,
  snapToGrid,
  translateFrame,
} from "./geometry";
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
const componentRegistry = useEditorRegistry();
const themeTokens = computed(() => resolveThemeTokens(store.document?.theme));
const host = ref<HTMLElement | null>(null);
const canvas = ref<HTMLElement | null>(null);
const zoom = ref(0.5);
const showGrid = ref(true);
const snapEnabled = ref(true);
const hoveredId = ref<string | null>(null);
const activeGuides = ref<ReturnType<typeof snapFrame>["guides"]>([]);
const activeOverlapIds = ref<string[]>([]);
const dataRuntime = createDataRuntime((componentId, parameters, signal) => {
  const document = store.document;
  if (!document) {
    return Promise.reject(new Error("The screen document is not loaded."));
  }
  return queryScreenDocument(
    structuredClone(toRaw(document)),
    componentId,
    parameters,
    signal,
  );
});
let clipboard: string[] = [];
let selecto: Selecto | null = null;
let moveable: Moveable | null = null;
const interactionStartFrames = new Map<string, ComponentInstance["frame"]>();
const interactionFinalPositions = new Map<string, { x: number; y: number }>();
const interactionFinalFrames = new Map<string, ComponentInstance["frame"]>();

const visibleComponents = computed(() =>
  (store.document?.components ?? []).filter(
    (component) => !component.state?.hidden,
  ),
);
const dataStates = computed(() => Object.fromEntries(
  visibleComponents.value.map((component) => [component.id, dataRuntime.state(component.id)]),
));
const parameterDefaults = computed(() =>
  Object.fromEntries(
    (store.document?.parameters ?? []).map((parameter) => [
      parameter.name,
      parameter.default ?? null,
    ]),
  ),
);
const boundComponentSignature = computed(() =>
  JSON.stringify(
    (store.document?.components ?? []).map((component) => ({
      id: component.id,
      data_binding: component.data_binding,
    })),
  ),
);
const selectedComponents = computed(() => {
  const selected = new Set(store.selection);
  return (store.document?.components ?? []).filter((component) =>
    selected.has(component.id),
  );
});
const selectionBounds = computed(() => {
  return getSelectionBounds(
    selectedComponents.value.map((component) => component.frame),
  );
});
const overlapIds = computed(() => {
  const ids = new Set(activeOverlapIds.value);
  if (!store.document) {
    return ids;
  }
  for (const component of selectedComponents.value) {
    const siblings = visibleComponents.value
      .filter((item) => item.id !== component.id)
      .map((item) => ({ id: item.id, frame: item.frame }));
    for (const id of snapFrame(
      { id: component.id, frame: component.frame },
      { canvas: store.document.canvas, siblings },
      { enabled: false },
    ).overlapIds) {
      ids.add(id);
    }
  }
  return ids;
});
const canvasStyle = computed(() => ({
  width: `${store.document?.canvas.width ?? 1920}px`,
  height: `${store.document?.canvas.height ?? 1080}px`,
  backgroundColor:
    typeof store.document?.canvas.background?.color === "string"
      ? store.document.canvas.background.color
      : typeof themeTokens.value.canvas_background === "string"
        ? themeTokens.value.canvas_background
        : "#071522",
  transform: `scale(${zoom.value})`,
}));
const stageStyle = computed(() => ({
  width: `${(store.document?.canvas.width ?? 1920) * zoom.value}px`,
  height: `${(store.document?.canvas.height ?? 1080) * zoom.value}px`,
}));

function componentById(id: string): ComponentInstance | undefined {
  return store.document?.components?.find((component) => component.id === id);
}

async function refreshData(): Promise<void> {
  if (!store.document) {
    return;
  }
  dataRuntime.beginGeneration();
  await Promise.all(
    visibleComponents.value
      .filter((component) => component.data_binding && component.data_binding.source !== "components" && Object.keys(component.data_binding).length > 0)
      .map((component) =>
        dataRuntime
          .load(
            component.id,
            component.data_binding!,
            parameterDefaults.value,
            component.type,
          )
          .catch(() => undefined),
      ),
  );
}

async function refreshComponentData(component: ComponentInstance): Promise<void> {
  if (!component.data_binding || Object.keys(component.data_binding).length === 0) {
    return;
  }
  await refreshData();
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
  finalPositions?: Record<string, { x: number; y: number }>,
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
          x: finalPositions?.[component.id]?.x ??
            (snapEnabled.value ? snapToGrid(translated.x) : translated.x),
          y: finalPositions?.[component.id]?.y ??
            (snapEnabled.value ? snapToGrid(translated.y) : translated.y),
        },
      ];
    }),
  );
  if (Object.keys(patches).length > 0) {
    store.dispatch({ type: "update_frames", patches });
  }
}

function normalizedResizeFrame(
  frame: ComponentInstance["frame"],
): ComponentInstance["frame"] {
  if (!store.document) return frame;
  const canvas = store.document.canvas;
  const snap = (value: number) =>
    snapEnabled.value ? snapToGrid(value) : value;
  const width = Math.min(canvas.width, Math.max(40, snap(frame.width)));
  const height = Math.min(canvas.height, Math.max(40, snap(frame.height)));
  return {
    ...frame,
    x: Math.min(Math.max(0, snap(frame.x)), canvas.width - width),
    y: Math.min(Math.max(0, snap(frame.y)), canvas.height - height),
    width,
    height,
  };
}

function commitResize(id: string, frame: ComponentInstance["frame"]): void {
  const component = componentById(id);
  if (!component || component.state?.locked || !store.document) {
    return;
  }
  const normalized = normalizedResizeFrame(frame);
  store.dispatch({
    type: "update_frame",
    component_ids: [id],
    patch: {
      x: normalized.x,
      y: normalized.y,
      width: normalized.width,
      height: normalized.height,
    },
  });
}

function commitResizeFrames(
  frames: Record<string, ComponentInstance["frame"]>,
): void {
  if (!store.document) return;
  const patches = Object.fromEntries(
    editable(Object.keys(frames)).map((component) => {
      const normalized = normalizedResizeFrame(frames[component.id]!);
      return [
        component.id,
        {
          x: normalized.x,
          y: normalized.y,
          width: normalized.width,
          height: normalized.height,
        },
      ];
    }),
  );
  if (Object.keys(patches).length > 0) {
    store.dispatch({ type: "update_frames", patches });
  }
}

function alignSelection(alignment: Alignment): void {
  const components = editable(store.selection);
  if (components.length < 2) {
    return;
  }
  store.dispatch({
    type: "update_frames",
    patches: alignFrames(
      components.map((component) => ({ id: component.id, frame: component.frame })),
      alignment,
    ),
  });
}

function distributeSelection(axis: "horizontal" | "vertical"): void {
  const components = editable(store.selection);
  if (components.length < 3) {
    return;
  }
  store.dispatch({
    type: "update_frames",
    patches: distributeFrames(
      components.map((component) => ({ id: component.id, frame: component.frame })),
      axis,
    ),
  });
}

function groupSelection(): void {
  const ids = editable(store.selection).map((component) => component.id);
  if (ids.length < 2) {
    return;
  }
  store.dispatch({
    type: "group_components",
    component_ids: ids,
    group_id: props.idFactory(),
  });
}

function ungroupSelection(): void {
  const groupIds = new Set(
    editable(store.selection)
      .map((component) => component.state?.group_id)
      .filter((groupId): groupId is string => Boolean(groupId)),
  );
  if (groupIds.size === 0) {
    return;
  }
  const ids = (store.document?.components ?? [])
    .filter((component) => component.state?.group_id && groupIds.has(component.state.group_id))
    .map((component) => component.id);
  store.dispatch({ type: "ungroup_components", component_ids: ids });
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

function duplicateSelection(): void {
  copySelection();
  pasteSelection();
}

function setZoom(value: number): void {
  zoom.value = Math.min(2, Math.max(0.1, value));
  if (moveable) {
    moveable.zoom = zoom.value;
    moveable.updateRect();
  }
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
  if (event.altKey && canvas.value) {
    const rect = canvas.value.getBoundingClientRect();
    const point = {
      x: (event.clientX - rect.left) / zoom.value,
      y: (event.clientY - rect.top) / zoom.value,
    };
    const underPointer = visibleComponents.value
      .filter(
        (component) =>
          point.x >= component.frame.x &&
          point.x <= component.frame.x + component.frame.width &&
          point.y >= component.frame.y &&
          point.y <= component.frame.y + component.frame.height,
      )
      .sort(
        (first, second) =>
          (second.frame.z_index ?? 0) - (first.frame.z_index ?? 0),
      );
    const currentIndex = underPointer.findIndex(
      (component) => component.id === store.selection[0],
    );
    const next = underPointer[(currentIndex + 1) % underPointer.length];
    if (next) {
      store.selection = [next.id];
    }
    return;
  }
  const component = componentById(id);
  const groupId = component?.state?.group_id;
  const groupMembers = groupId
    ? visibleComponents.value
        .filter((item) => item.state?.group_id === groupId)
        .map((item) => item.id)
    : [id];
  if (event.metaKey || event.ctrlKey || event.shiftKey) {
    store.selection = store.selection.includes(id)
      ? store.selection.filter((selectedId) => selectedId !== id)
      : [...store.selection, ...groupMembers.filter((memberId) => !store.selection.includes(memberId))];
  } else {
    store.selection = groupMembers;
  }
}

function toggleGrid(): void {
  showGrid.value = !showGrid.value;
}

function toggleSnap(): void {
  snapEnabled.value = !snapEnabled.value;
}

function keyboard(event: KeyboardEvent): void {
  const target = event.target;
  if (
    target instanceof HTMLInputElement ||
    target instanceof HTMLTextAreaElement ||
    target instanceof HTMLSelectElement ||
    (target instanceof HTMLElement && target.isContentEditable)
  ) {
    return;
  }
  const modifier = event.metaKey || event.ctrlKey;
  if (modifier && event.key.toLowerCase() === "z") {
    event.preventDefault();
    event.shiftKey ? store.redo() : store.undo();
  } else if (modifier && event.key.toLowerCase() === "y") {
    event.preventDefault();
    store.redo();
  } else if (modifier && event.key.toLowerCase() === "c") {
    event.preventDefault();
    copySelection();
  } else if (modifier && event.key.toLowerCase() === "v") {
    event.preventDefault();
    pasteSelection();
  } else if (modifier && event.key.toLowerCase() === "d") {
    event.preventDefault();
    duplicateSelection();
  } else if (modifier && event.key.toLowerCase() === "g") {
    event.preventDefault();
    event.shiftKey ? ungroupSelection() : groupSelection();
  } else if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) {
    const distance = event.shiftKey ? 10 : 1;
    const delta = {
      x: event.key === "ArrowLeft" ? -distance : event.key === "ArrowRight" ? distance : 0,
      y: event.key === "ArrowUp" ? -distance : event.key === "ArrowDown" ? distance : 0,
    };
    const ids = editable(store.selection).map((component) => component.id);
    if (ids.length > 0) {
      event.preventDefault();
      commitDrag(ids, { dx: delta.x, dy: delta.y });
    }
  } else if (event.key === "Escape") {
    event.preventDefault();
    store.selection = [];
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
    .filter((id) => !componentById(id)?.state?.locked)
    .map((id) =>
      canvas.value?.querySelector<HTMLElement>(
        `[data-canvas-component="${CSS.escape(id)}"]`,
      ),
    )
    .filter((element): element is HTMLElement => Boolean(element));
  moveable.updateRect();
}

function beginInteraction(): void {
  interactionStartFrames.clear();
  interactionFinalPositions.clear();
  interactionFinalFrames.clear();
  for (const component of editable(store.selection)) {
    interactionStartFrames.set(component.id, { ...component.frame });
  }
}

function finishInteraction(): void {
  interactionStartFrames.clear();
  interactionFinalPositions.clear();
  interactionFinalFrames.clear();
  activeGuides.value = [];
  activeOverlapIds.value = [];
  void updateMoveableTargets();
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
    selecto.on("dragStart", (event) => {
      const target = event.inputEvent.target;
      const selectedTargets = store.selection
        .map((id) =>
          canvas.value?.querySelector<HTMLElement>(
            `[data-canvas-component="${CSS.escape(id)}"]`,
          ),
        )
        .filter((element): element is HTMLElement => Boolean(element));
      if (
        target instanceof Element &&
        (moveable?.isMoveableElement(target) ||
          selectedTargets.some(
            (element) => element === target || element.contains(target),
          ))
      ) {
        event.stop();
      }
    });
    selecto.on("selectEnd", (event) => {
      if (event.isClick) {
        return;
      }
      store.selection = event.selected
        .map((element) => element.getAttribute("data-canvas-component"))
        .filter((id): id is string => Boolean(id));
    });
    moveable = new Moveable(host.value, {
      target: [],
      rootContainer: document.body,
      zoom: zoom.value,
      draggable: true,
      resizable: true,
      origin: false,
      snappable: false,
    });
    moveable.on("dragStart", (event) => {
      beginInteraction();
      event.datas.startFrames = new Map(interactionStartFrames);
    });
    moveable.on("drag", (event) => {
      const id = event.target.getAttribute("data-canvas-component");
      const start = id ? interactionStartFrames.get(id) : undefined;
      const current = id ? componentById(id) : undefined;
      if (!id || !start || !current || !store.document) {
        return;
      }
      const siblings = visibleComponents.value
        .filter((component) => component.id !== id)
        .map((component) => ({ id: component.id, frame: component.frame }));
      const inputEvent = event.inputEvent as MouseEvent | TouchEvent | undefined;
      const disableSnap = inputEvent instanceof MouseEvent && inputEvent.altKey;
      const snapped = snapFrame(
        {
          id,
          frame: { ...current.frame, x: event.left, y: event.top },
        },
        { canvas: store.document.canvas, siblings },
        { enabled: snapEnabled.value && !disableSnap },
      );
      activeGuides.value = snapped.guides;
      activeOverlapIds.value = snapped.overlapIds;
      const target = event.target as HTMLElement;
      target.style.left = `${snapped.frame.x}px`;
      target.style.top = `${snapped.frame.y}px`;
      interactionFinalPositions.set(id, {
        x: snapped.frame.x,
        y: snapped.frame.y,
      });
    });
    moveable.on("dragEnd", (event) => {
      const id = event.target.getAttribute("data-canvas-component");
      const start = id ? interactionStartFrames.get(id) : undefined;
      if (id && start) {
        const finalPosition = interactionFinalPositions.get(id);
        if (finalPosition) {
          commitDrag(
            [id],
            {
              dx: finalPosition.x - start.x,
              dy: finalPosition.y - start.y,
            },
            { [id]: finalPosition },
          );
        }
      }
      finishInteraction();
    });
    moveable.on("dragGroupStart", () => {
      beginInteraction();
    });
    moveable.on("dragGroup", (event) => {
      if (!store.document || interactionStartFrames.size < 2) {
        return;
      }
      const firstEvent = event.events.find((item) => {
        const id = item.target.getAttribute("data-canvas-component");
        return id ? interactionStartFrames.has(id) : false;
      });
      const firstId = firstEvent?.target.getAttribute("data-canvas-component");
      const firstStart = firstId ? interactionStartFrames.get(firstId) : undefined;
      const frames = [...interactionStartFrames.entries()].map(([id, frame]) => ({
        id,
        frame,
      }));
      const bounds = getSelectionBounds(frames.map((item) => item.frame));
      if (!firstEvent || !firstStart || !bounds) {
        return;
      }
      const requestedDelta = {
        x: firstEvent.left - firstStart.x,
        y: firstEvent.top - firstStart.y,
      };
      const selected = new Set(interactionStartFrames.keys());
      const siblings = visibleComponents.value
        .filter((component) => !selected.has(component.id))
        .map((component) => ({ id: component.id, frame: component.frame }));
      const inputEvent = event.inputEvent as MouseEvent | TouchEvent | undefined;
      const disableSnap = inputEvent instanceof MouseEvent && inputEvent.altKey;
      const snapped = snapFrame(
        {
          id: "__selection__",
          frame: {
            x: bounds.x + requestedDelta.x,
            y: bounds.y + requestedDelta.y,
            width: bounds.width,
            height: bounds.height,
          },
        },
        { canvas: store.document.canvas, siblings },
        { enabled: snapEnabled.value && !disableSnap },
      );
      const delta = {
        x: snapped.frame.x - bounds.x,
        y: snapped.frame.y - bounds.y,
      };
      activeGuides.value = snapped.guides;
      activeOverlapIds.value = snapped.overlapIds;
      for (const item of event.events) {
        const id = item.target.getAttribute("data-canvas-component");
        const start = id ? interactionStartFrames.get(id) : undefined;
        if (!start) continue;
        const target = item.target as HTMLElement;
        target.style.left = `${start.x + delta.x}px`;
        target.style.top = `${start.y + delta.y}px`;
        interactionFinalPositions.set(id!, {
          x: start.x + delta.x,
          y: start.y + delta.y,
        });
      }
    });
    moveable.on("dragGroupEnd", () => {
      const positions = Object.fromEntries(interactionFinalPositions);
      const ids = Object.keys(positions);
      if (ids.length > 0) {
        commitDrag(ids, { dx: 0, dy: 0 }, positions);
      }
      finishInteraction();
    });
    moveable.on("resizeStart", () => {
      beginInteraction();
    });
    moveable.on("resize", (event) => {
      const target = event.target as HTMLElement;
      const id = target.getAttribute("data-canvas-component");
      const start = id ? interactionStartFrames.get(id) : undefined;
      if (!id || !start) return;
      const frame = {
        ...start,
        x: event.drag?.left ?? start.x,
        y: event.drag?.top ?? start.y,
        width: event.width,
        height: event.height,
      };
      target.style.width = `${event.width}px`;
      target.style.height = `${event.height}px`;
      if (event.drag) {
        target.style.left = `${event.drag.left}px`;
        target.style.top = `${event.drag.top}px`;
      }
      interactionFinalFrames.set(id, frame);
    });
    moveable.on("resizeEnd", (event) => {
      const id = event.target.getAttribute("data-canvas-component");
      const frame = id ? interactionFinalFrames.get(id) : undefined;
      if (id && frame) {
        commitResize(id, frame);
      }
      finishInteraction();
    });
    moveable.on("resizeGroupStart", () => {
      beginInteraction();
    });
    moveable.on("resizeGroup", (event) => {
      for (const item of event.events) {
        const target = item.target as HTMLElement;
        const id = target.getAttribute("data-canvas-component");
        const start = id ? interactionStartFrames.get(id) : undefined;
        if (!id || !start) continue;
        const frame = {
          ...start,
          x: item.drag?.left ?? start.x,
          y: item.drag?.top ?? start.y,
          width: item.width,
          height: item.height,
        };
        target.style.left = `${frame.x}px`;
        target.style.top = `${frame.y}px`;
        target.style.width = `${frame.width}px`;
        target.style.height = `${frame.height}px`;
        interactionFinalFrames.set(id, frame);
      }
    });
    moveable.on("resizeGroupEnd", () => {
      commitResizeFrames(Object.fromEntries(interactionFinalFrames));
      finishInteraction();
    });
    void updateMoveableTargets();
  }
});

watch(() => store.selection, () => void updateMoveableTargets(), {
  deep: true,
});

watch(boundComponentSignature, () => void refreshData(), { immediate: true });

onBeforeUnmount(() => {
  window.removeEventListener("keydown", keyboard);
  selecto?.destroy();
  moveable?.destroy();
  dataRuntime.dispose();
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
  commitResizeFrames,
  copySelection,
  duplicateSelection,
  distributeSelection,
  fitToViewport,
  pasteSelection,
  selectionBounds,
  setZoom,
  groupSelection,
  refreshData,
  ungroupSelection,
  showGrid,
  snapEnabled,
  toggleGrid,
  toggleSnap,
  zoom,
});
</script>

<template>
  <div ref="host" class="screen-canvas-host">
    <div class="screen-canvas-stage" :style="stageStyle">
      <div
        ref="canvas"
        class="screen-canvas"
        :class="{ 'has-grid': showGrid }"
        :style="canvasStyle"
      >
        <div
          v-for="(guide, index) in activeGuides"
          :key="`${guide.orientation}-${guide.position}-${index}`"
          class="canvas-guide"
          :class="`is-${guide.orientation}`"
          :style="
            guide.orientation === 'vertical'
              ? { left: `${guide.position}px`, top: 0, height: `${store.document?.canvas.height ?? 1080}px` }
              : { top: `${guide.position}px`, left: 0, width: `${store.document?.canvas.width ?? 1920}px` }
          "
          data-canvas-guide
        />
        <div
          v-for="component in visibleComponents"
          :key="component.id"
          class="editor-canvas-component"
          :class="{
            'is-selected': store.selection.includes(component.id),
            'is-locked': component.state?.locked,
            'is-hovered': hoveredId === component.id,
            'is-overlapped': overlapIds.has(component.id),
          }"
          role="button"
          tabindex="0"
          :data-canvas-component="component.id"
          :style="{
            left: `${component.frame.x}px`,
            top: `${component.frame.y}px`,
            width: `${component.frame.width}px`,
            height: `${component.frame.height}px`,
            zIndex: component.frame.z_index ?? 0,
          }"
          @mouseenter="hoveredId = component.id"
          @mouseleave="hoveredId = null"
          @click.stop="selectComponent(component.id, $event)"
          @keydown.enter.stop="store.selection = [component.id]"
        >
          <span
            v-if="hoveredId === component.id || store.selection.includes(component.id) || overlapIds.has(component.id)"
            class="canvas-component-label"
          >
            {{ componentRegistry.get(component.type)?.label ?? component.type }}
          </span>
          <ComponentHost
            :definition="componentRegistry.get(component.type)"
            :instance="component"
            :load-asset="loadAsset"
            :query-state="dataRuntime.state(component.id)"
            :data-states="dataStates"
            :parameters="parameterDefaults"
            :theme="themeTokens"
            mode="editor"
          />
          <div
            v-if="dataRuntime.state(component.id).status === 'error'"
            class="canvas-component-error"
          >
            <span>数据加载失败</span>
            <button
              type="button"
              :data-retry-component-data="component.id"
              @click.stop="refreshComponentData(component)"
            >
              重试
            </button>
          </div>
        </div>
      </div>
    </div>
    <div class="canvas-status" data-canvas-status>
      <span>{{ store.document?.canvas.width ?? 1920 }} × {{ store.document?.canvas.height ?? 1080 }}</span>
      <span>{{ Math.round(zoom * 100) }}%</span>
      <span>{{ showGrid ? "网格 10px" : "网格关闭" }}</span>
      <span>{{ snapEnabled ? "吸附开启" : "吸附关闭" }}</span>
      <span v-if="store.selection.length">已选 {{ store.selection.length }} 个组件</span>
    </div>
  </div>
</template>
