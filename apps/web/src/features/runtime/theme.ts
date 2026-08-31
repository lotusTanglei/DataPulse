import type { DashboardDocument } from "../../contracts";
import type { JsonValue } from "../query/types";

type DashboardTheme = DashboardDocument["theme"];

export const DEFAULT_THEME_TOKENS: Record<string, JsonValue> = {
  canvas_background: "#071522",
  panel_background: "#0b1b2b",
  panel_background_alt: "#10253a",
  panel_border: "#1b4160",
  panel_radius: 8,
  text_primary: "#edf7ff",
  text_secondary: "#9ab3c8",
  text_muted: "#638198",
  accent: "#26d9c1",
  info: "#3b8df4",
  success: "#43d17d",
  warning: "#f3b638",
  danger: "#f16d75",
  progress_track: "#173149",
  chart_grid: "rgba(148, 163, 184, 0.14)",
  chart_axis: "#1b4160",
  chart_colors: [
    "#26d9c1",
    "#3b8df4",
    "#8a9ff0",
    "#f3b638",
    "#f16d75",
    "#a5d85b",
  ],
  font_family: "Inter, PingFang SC, Microsoft YaHei, sans-serif",
};

function tokenName(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9-]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function resolveTheme(
  theme: DashboardTheme | null | undefined,
): Record<string, string> {
  const resolved: Record<string, string> = {};
  for (const [name, value] of Object.entries(theme?.tokens ?? {})) {
    const safeName = tokenName(name);
    if (
      safeName.length > 0 &&
      (typeof value === "string" || typeof value === "number")
    ) {
      const resolvedValue = String(value);
      resolved[`--dp-${safeName}`] = resolvedValue;
      const screenName = safeName.startsWith("screen-")
        ? safeName.slice("screen-".length)
        : safeName;
      resolved[`--screen-${screenName}`] = resolvedValue;
    }
  }
  return resolved;
}

export function resolveThemeTokens(
  theme: DashboardTheme | null | undefined,
): Record<string, JsonValue> {
  return {
    ...DEFAULT_THEME_TOKENS,
    ...(theme?.tokens ?? {}),
  };
}
