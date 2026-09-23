import { Validator, type Schema } from "jsonschema";
import type { JsonValue } from "../query/types";

/** Interpret Draft 7 directly; never compile schemas with eval/new Function. */
export function matchesPluginSchema(schema: Record<string, JsonValue>, value: unknown): boolean {
  return new Validator().validate(value, schema as Schema, { skipAttributes: ["format"] }).valid;
}

export function isJsonValue(value: unknown, ancestors = new Set<object>()): value is JsonValue {
  if (value === null || typeof value === "string" || typeof value === "boolean") return true;
  if (typeof value === "number") return Number.isFinite(value);
  if (typeof value !== "object" || ancestors.has(value)) return false;
  if (!Array.isArray(value) && Object.getPrototypeOf(value) !== Object.prototype && Object.getPrototypeOf(value) !== null) return false;
  ancestors.add(value);
  const valid = Object.values(value).every((child) => isJsonValue(child, ancestors));
  ancestors.delete(value);
  return valid;
}
