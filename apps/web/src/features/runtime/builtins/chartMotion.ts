export function applyChartMotionPreference<T extends Record<string, unknown>>(
  option: T,
): T {
  if (
    typeof window === "undefined" ||
    typeof window.matchMedia !== "function" ||
    !window.matchMedia("(prefers-reduced-motion: reduce)").matches
  ) {
    return option;
  }
  return {
    ...option,
    animation: false,
    animationDuration: 0,
    animationDurationUpdate: 0,
  };
}
