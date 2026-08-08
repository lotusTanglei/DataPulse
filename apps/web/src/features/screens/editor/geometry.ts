import type { ComponentFrame } from "./commands";

export interface Point {
  x: number;
  y: number;
}

export interface CanvasSize {
  width: number;
  height: number;
}

export interface FrameItem {
  id: string;
  frame: ComponentFrame;
}

export interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export type GuideOrientation = "horizontal" | "vertical";
export type GuideKind = "grid" | "edge" | "center" | "spacing";

export interface SnapGuide {
  orientation: GuideOrientation;
  position: number;
  start: number;
  end: number;
  kind: GuideKind;
  sourceId?: string;
}

export interface SnapContext {
  canvas: CanvasSize;
  siblings: FrameItem[];
  gridSize?: number;
  threshold?: number;
}

export interface SnapResult {
  frame: ComponentFrame;
  guides: SnapGuide[];
  overlapIds: string[];
}

export function snapToGrid(value: number, gridSize = 10): number {
  if (gridSize <= 0) {
    return value;
  }
  return Math.round(value / gridSize) * gridSize;
}

export function translateFrame(
  frame: ComponentFrame,
  delta: Point,
  canvas: CanvasSize,
): ComponentFrame {
  return {
    ...frame,
    x: Math.min(
      Math.max(0, frame.x + delta.x),
      Math.max(0, canvas.width - frame.width),
    ),
    y: Math.min(
      Math.max(0, frame.y + delta.y),
      Math.max(0, canvas.height - frame.height),
    ),
  };
}

export function selectionBounds(frames: ComponentFrame[]): Rect | null {
  if (frames.length === 0) {
    return null;
  }
  const left = Math.min(...frames.map((frame) => frame.x));
  const top = Math.min(...frames.map((frame) => frame.y));
  const right = Math.max(...frames.map((frame) => frame.x + frame.width));
  const bottom = Math.max(...frames.map((frame) => frame.y + frame.height));
  return { x: left, y: top, width: right - left, height: bottom - top };
}

function clampFrame(frame: ComponentFrame, canvas: CanvasSize): ComponentFrame {
  return {
    ...frame,
    x: Math.min(Math.max(0, frame.x), Math.max(0, canvas.width - frame.width)),
    y: Math.min(Math.max(0, frame.y), Math.max(0, canvas.height - frame.height)),
  };
}

function rectsOverlap(first: ComponentFrame, second: ComponentFrame): boolean {
  return (
    first.x < second.x + second.width &&
    first.x + first.width > second.x &&
    first.y < second.y + second.height &&
    first.y + first.height > second.y
  );
}

function axisTargets(
  moving: FrameItem,
  siblings: FrameItem[],
  axis: "x" | "y",
  canvas: CanvasSize,
): Array<{ position: number; kind: GuideKind; sourceId?: string }> {
  const canvasLength = axis === "x" ? canvas.width : canvas.height;
  const targets: Array<{ position: number; kind: GuideKind; sourceId?: string }> = [
    { position: 0, kind: "edge" },
    { position: canvasLength, kind: "edge" },
    ...siblings
      .filter((item) => item.id !== moving.id)
      .flatMap((item) => {
        const start = axis === "x" ? item.frame.x : item.frame.y;
        const end = start + (axis === "x" ? item.frame.width : item.frame.height);
        return [
          { position: start, kind: "edge" as const, sourceId: item.id },
          { position: end, kind: "edge" as const, sourceId: item.id },
          {
            position: start + (end - start) / 2,
            kind: "center" as const,
            sourceId: item.id,
          },
        ];
      }),
  ];
  return targets;
}

function snapAxis(
  position: number,
  size: number,
  moving: FrameItem,
  siblings: FrameItem[],
  axis: "x" | "y",
  context: SnapContext,
): { position: number; guide: SnapGuide | null } {
  const gridSize = context.gridSize ?? 10;
  const threshold = context.threshold ?? 8;
  const gridPosition = snapToGrid(position, gridSize);
  let best: { position: number; distance: number; guide: SnapGuide } = {
    position: gridPosition,
    distance: Math.abs(gridPosition - position),
    guide: {
      orientation: axis === "x" ? "vertical" : "horizontal",
      position: gridPosition,
      start: axis === "x" ? 0 : position,
      end: axis === "x" ? position + size : position + size,
      kind: "grid" as const,
    },
  };

  for (const target of axisTargets(moving, siblings, axis, context.canvas)) {
    for (const offset of [0, size / 2, size]) {
      const candidate = target.position - offset;
      const distance = Math.abs(candidate - position);
      if (distance <= threshold && distance < best.distance) {
        best = {
          position: candidate,
          distance,
          guide: {
            orientation: axis === "x" ? "vertical" : "horizontal",
            position: target.position,
            start: axis === "x" ? 0 : position,
            end: axis === "x" ? context.canvas.width : position + size,
            kind: target.kind,
            sourceId: target.sourceId,
          },
        };
      }
    }
  }

  return {
    position: best.distance <= threshold ? best.position : position,
    guide: best.distance <= threshold ? best.guide : null,
  };
}

export function snapFrame(
  moving: FrameItem,
  context: SnapContext,
  options: { enabled?: boolean } = {},
): SnapResult {
  const enabled = options.enabled ?? true;
  const base = clampFrame(moving.frame, context.canvas);
  if (!enabled) {
    return {
      frame: base,
      guides: [],
      overlapIds: context.siblings
        .filter((item) => item.id !== moving.id && rectsOverlap(base, item.frame))
        .map((item) => item.id),
    };
  }
  const x = snapAxis(
    base.x,
    base.width,
    { ...moving, frame: base },
    context.siblings,
    "x",
    context,
  );
  const y = snapAxis(
    base.y,
    base.height,
    { ...moving, frame: { ...base, x: x.position } },
    context.siblings,
    "y",
    context,
  );
  const frame = clampFrame({ ...base, x: x.position, y: y.position }, context.canvas);
  return {
    frame,
    guides: [x.guide, y.guide].filter((guide): guide is SnapGuide => guide !== null),
    overlapIds: context.siblings
      .filter((item) => item.id !== moving.id && rectsOverlap(frame, item.frame))
      .map((item) => item.id),
  };
}

export type Alignment = "left" | "center" | "right" | "top" | "middle" | "bottom";

export function alignFrames(
  items: FrameItem[],
  alignment: Alignment,
): Record<string, Partial<ComponentFrame>> {
  const bounds = selectionBounds(items.map((item) => item.frame));
  if (!bounds) {
    return {};
  }
  return Object.fromEntries(
    items.map((item) => {
      const frame = item.frame;
      const patch =
        alignment === "left"
          ? { x: bounds.x }
          : alignment === "center"
            ? { x: bounds.x + (bounds.width - frame.width) / 2 }
            : alignment === "right"
              ? { x: bounds.x + bounds.width - frame.width }
              : alignment === "top"
                ? { y: bounds.y }
                : alignment === "middle"
                  ? { y: bounds.y + (bounds.height - frame.height) / 2 }
                  : { y: bounds.y + bounds.height - frame.height };
      return [item.id, patch];
    }),
  );
}

export function distributeFrames(
  items: FrameItem[],
  axis: "horizontal" | "vertical",
): Record<string, Partial<ComponentFrame>> {
  if (items.length < 3) {
    return Object.fromEntries(items.map((item) => [item.id, {}]));
  }
  const sorted = [...items].sort((first, second) =>
    axis === "horizontal"
      ? first.frame.x - second.frame.x
      : first.frame.y - second.frame.y,
  );
  const start = sorted[0]!.frame;
  const end = sorted.at(-1)!.frame;
  const span =
    axis === "horizontal"
      ? end.x + end.width - start.x
      : end.y + end.height - start.y;
  const totalSize = sorted.reduce(
    (sum, item) => sum + (axis === "horizontal" ? item.frame.width : item.frame.height),
    0,
  );
  const gap = (span - totalSize) / (sorted.length - 1);
  let cursor = axis === "horizontal" ? start.x : start.y;
  const patches: Record<string, Partial<ComponentFrame>> = {};
  for (const item of sorted) {
    const position = axis === "horizontal" ? item.frame.x : item.frame.y;
    patches[item.id] =
      Math.abs(position - cursor) > 0.5
        ? axis === "horizontal"
          ? { x: cursor }
          : { y: cursor }
        : {};
    cursor += (axis === "horizontal" ? item.frame.width : item.frame.height) + gap;
  }
  return patches;
}
