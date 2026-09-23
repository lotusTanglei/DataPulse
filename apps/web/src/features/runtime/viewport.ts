export type RuntimeDensity = "comfortable" | "compact" | "scroll";

export interface RuntimeViewportInput {
  canvasWidth: number;
  canvasHeight: number;
  containerWidth: number;
  containerHeight: number;
}

export interface RuntimeViewport {
  density: RuntimeDensity;
  overflow: boolean;
  scale: number;
  viewportHeight: number;
  viewportWidth: number;
}

const COMPACT_SCALE = 0.75;
const MIN_READABLE_SCALE = 0.5;

export function resolveRuntimeViewport({
  canvasWidth,
  canvasHeight,
  containerWidth,
  containerHeight,
}: RuntimeViewportInput): RuntimeViewport {
  if (
    canvasWidth <= 0 ||
    canvasHeight <= 0 ||
    containerWidth <= 0
  ) {
    return {
      density: "comfortable",
      overflow: false,
      scale: 1,
      viewportHeight: canvasHeight,
      viewportWidth: canvasWidth,
    };
  }
  const widthScale = containerWidth / canvasWidth;
  const heightScale =
    containerHeight > 0 ? containerHeight / canvasHeight : widthScale;
  const fitScale = Math.min(widthScale, heightScale);
  const overflow = fitScale < MIN_READABLE_SCALE;
  const scale = overflow ? 1 : fitScale;
  const density: RuntimeDensity = overflow
    ? "scroll"
    : fitScale < COMPACT_SCALE
      ? "compact"
      : "comfortable";
  return {
    density,
    overflow,
    scale,
    viewportHeight: canvasHeight * scale,
    viewportWidth: canvasWidth * scale,
  };
}
