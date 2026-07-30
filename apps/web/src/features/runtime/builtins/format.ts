import type { JsonValue, QueryResult } from "../../query/types";

export function stringProp(
  props: Record<string, JsonValue> | undefined,
  name: string,
  fallback = "",
): string {
  const value = props?.[name];
  return typeof value === "string" ? value : fallback;
}

export function numberProp(
  props: Record<string, JsonValue> | undefined,
  name: string,
  fallback: number,
  bounds?: { min: number; max: number },
): number {
  const value = props?.[name];
  const resolved =
    typeof value === "number" && Number.isFinite(value) ? value : fallback;
  return bounds
    ? Math.min(bounds.max, Math.max(bounds.min, resolved))
    : resolved;
}

export function firstValue(result: QueryResult | null): JsonValue | undefined {
  return result?.rows[0]?.[0];
}

export function numericValue(value: JsonValue | undefined): number | null {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }
  if (typeof value === "string" && value.trim().length > 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

export function formatNumber(value: number, precision: number): string {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  }).format(value);
}

export function formatCell(value: JsonValue | undefined): string {
  if (value === null || value === undefined) {
    return "—";
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
