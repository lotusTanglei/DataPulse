import type { DashboardDocument } from "../../contracts";

type DashboardTheme = DashboardDocument["theme"];

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
      resolved[`--screen-${safeName}`] = resolvedValue;
    }
  }
  return resolved;
}
