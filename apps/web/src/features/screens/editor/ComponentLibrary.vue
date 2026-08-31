<script setup lang="ts">
import {
  Activity,
  BellRing,
  ChartLine,
  ChartNoAxesColumn,
  ChartPie,
  ChartSpline,
  Clock3,
  Funnel,
  Gauge,
  Grid2x2,
  Hash,
  Image,
  Map as MapIcon,
  Minus,
  PanelTop,
  Radar,
  Rows3,
  Table2,
  Trophy,
  Type,
} from "@lucide/vue";
import { defaultComponentRegistry } from "../../runtime/registry";
import { computed, type Component } from "vue";
import type { ComponentFrame } from "./commands";
import { snapToGrid } from "./geometry";
import { useScreenEditorStore } from "./store";

const store = useScreenEditorStore();
const groups = computed(() => {
  const grouped = new Map<string, ReturnType<typeof defaultComponentRegistry.list>>();
  for (const definition of defaultComponentRegistry.list()) {
    const category = definition.category ?? "其他";
    const definitions = grouped.get(category) ?? [];
    definitions.push(definition);
    grouped.set(category, definitions);
  }
  return [...grouped.entries()];
});

const iconMap: Record<string, Component> = {
  "builtin.text": Type,
  "builtin.image": Image,
  "builtin.panel": PanelTop,
  "builtin.divider": Minus,
  "builtin.digital_number": Hash,
  "builtin.kpi": Activity,
  "builtin.table": Table2,
  "builtin.progress": Rows3,
  "builtin.gauge": Gauge,
  "builtin.status_matrix": Grid2x2,
  "builtin.line": ChartLine,
  "builtin.bar": ChartNoAxesColumn,
  "builtin.pie": ChartPie,
  "builtin.radar": Radar,
  "builtin.heatmap": Grid2x2,
  "builtin.scatter": ChartSpline,
  "builtin.funnel": Funnel,
  "builtin.ranking": Trophy,
  "builtin.alert_list": BellRing,
  "builtin.timeline": Clock3,
  "builtin.geo_map": MapIcon,
};

function componentIcon(type: string): Component {
  return iconMap[type] ?? Activity;
}

function previewKind(type: string): string {
  if (["builtin.line"].includes(type)) return "line";
  if (["builtin.bar", "builtin.ranking", "builtin.progress"].includes(type)) return "bars";
  if (["builtin.pie"].includes(type)) return "pie";
  if (["builtin.gauge"].includes(type)) return "gauge";
  if (["builtin.table", "builtin.status_matrix"].includes(type)) return "table";
  if (["builtin.alert_list", "builtin.timeline"].includes(type)) return "list";
  if (["builtin.digital_number", "builtin.kpi"].includes(type)) return "number";
  if (["builtin.panel", "builtin.image", "builtin.geo_map"].includes(type)) return "panel";
  return "line";
}

function previewBars(type: string): number[] {
  return type === "builtin.ranking" ? [40, 68, 52, 84] : [30, 58, 44, 76, 63];
}

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
      style: structuredClone(definition.defaultStyle ?? {}),
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
    <div v-for="[category, definitions] in groups" :key="category" class="component-library__group">
      <h3>{{ category }}</h3>
      <div class="component-library__grid">
        <button
          v-for="definition in definitions"
          :key="definition.type"
          type="button"
          :title="`${definition.label}${definition.dataCapability === 'none' ? '' : ' · 支持演示数据'}`"
          @click="add(definition.type)"
        >
          <span
            class="component-library__preview"
            :data-preview="previewKind(definition.type)"
            aria-hidden="true"
          >
            <component
              :is="componentIcon(definition.type)"
              class="component-library__icon"
              :size="15"
              :stroke-width="1.8"
            />
            <span class="component-library__mini-visual">
              <i
                v-for="height in previewBars(definition.type)"
                :key="height"
                :style="{ height: `${height}%` }"
              />
            </span>
          </span>
          <span class="component-library__label">{{ definition.label }}</span>
          <small v-if="definition.dataCapability !== 'none'">数据</small>
        </button>
      </div>
    </div>
  </section>
</template>
