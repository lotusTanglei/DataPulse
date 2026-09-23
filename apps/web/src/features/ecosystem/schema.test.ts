import { afterEach, expect, it, vi } from "vitest";
import { matchesPluginSchema } from "./schema";

afterEach(() => vi.unstubAllGlobals());

it("interprets properties and local Draft 7 tuple references without code generation", () => {
  vi.stubGlobal("Function", function () { throw new Error("unsafe-eval blocked"); });
  const schema = {
    $schema: "http://json-schema.org/draft-07/schema#",
    type: "object",
    definitions: { label: { type: "string", minLength: 1 } },
    properties: {
      values: { type: "array", items: [{ $ref: "#/definitions/label" }], additionalItems: false },
    },
    required: ["values"],
    additionalProperties: false,
  };
  expect(matchesPluginSchema(schema, { values: ["Total"] })).toBe(true);
  for (const invalid of [{ values: [2] }, { values: [""] }, { values: ["a", "b"] }, {}]) {
    expect(matchesPluginSchema(schema, invalid)).toBe(false);
  }
});

it("enforces conditional schemas and treats format as an annotation on both hosts", () => {
  const schema = {
    type: "object",
    properties: { mode: { type: "string" }, url: { type: "string", format: "uri" } },
    if: { properties: { mode: { const: "remote" } } },
    then: { required: ["url"] },
  };
  expect(matchesPluginSchema(schema, { mode: "remote" })).toBe(false);
  expect(matchesPluginSchema(schema, { mode: "remote", url: "annotation only" })).toBe(true);
  expect(matchesPluginSchema(schema, { mode: "local" })).toBe(true);
});
