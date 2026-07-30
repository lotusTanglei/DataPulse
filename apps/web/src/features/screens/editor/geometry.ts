import type { ComponentFrame } from "./commands";

export interface Point {
  x: number;
  y: number;
}

export interface CanvasSize {
  width: number;
  height: number;
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
