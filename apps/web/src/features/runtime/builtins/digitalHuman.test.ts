import { describe, expect, test } from "vitest";

import type { DigitalHumanSpec } from "@datapulse/schema";
import type { QueryResult } from "../../query/types";
import { buildSpeechPlan, canTransitionSpeechStatus, defaultDigitalHumanConfig, evaluateSpeechConditions, isWithinSpeechWindow, parseSpeechTemplate, renderSpeechTemplate, resolveSpeechRecording, resultFingerprint, sensitiveSpeechField } from "./digitalHuman";
import type { ComponentInstance, ComponentQueryState } from "../types";

const result: QueryResult = {
  request_id: "r1",
  columns: [
    { name: "sales", data_type: "number" },
    { name: "region", data_type: "text" },
  ],
  rows: [[1234.5, "华东"]],
  row_count: 1,
  truncated: false,
  duration_ms: 1,
};

describe("digital human speech templates", () => {
  test("renders named and first-value aliases with formatting", () => {
    expect(renderSpeechTemplate("{{region}}销售额 {{sales | number}}", result)).toBe("华东销售额 1,234.5");
    expect(renderSpeechTemplate("当前值 {{value | percent}}", { ...result, rows: [[0.456]] })).toBe("当前值 45.6%");
  });

  test("uses a stable fingerprint for the current data generation", () => {
    expect(resultFingerprint(result)).toBe(resultFingerprint(structuredClone(result)));
    expect(resultFingerprint(null)).toBe("empty");
  });

  test("renders structured paragraphs and emphasis around explicit pauses", () => {
    const plan = buildSpeechPlan({
      id: "structured", type: "builtin.digital_human", frame: { x: 0, y: 0, width: 320, height: 420 },
      props: {
        speech_template: "旧模板",
        speech_segments: [
          { kind: "paragraph", text: "销售额 {{sales | number}}" },
          { kind: "pause", duration_ms: 800 },
          { kind: "emphasis", text: "重点区域 {{region}}" },
        ],
      },
      data_binding: {},
    }, { result, status: "success", error: null });
    expect(plan.text).toBe("销售额 1,234.5\n重点区域 华东");
    expect(plan.code).toBeNull();
  });
});

const speaker: ComponentInstance = {
  id: "speaker", type: "builtin.digital_human", frame: { x: 0, y: 0, width: 320, height: 420 },
  props: { speech_template: "本月 {{sales.amount | number}}，状态 {{state}}" },
  data_binding: { source: "components", variables: [
    { name: "sales.amount", component_id: "sales", field: "sales", unit: "元" },
    { name: "state", component_id: "states", field: "status", enum_labels: { ok: "正常" } },
  ] },
};
const idle: ComponentQueryState = { status: "idle", result: null, error: null };

test("prerecorded sound requires a confirmed media version and the current rendered transcript", () => {
  const config = { ...defaultDigitalHumanConfig, audio_asset_id: "voice" };
  expect(resolveSpeechRecording(config, "Sales 123").code).toBe("SPEECH_RECORDING_UNCONFIRMED");
  const recording = { asset_id: "voice", sha256: "a".repeat(64), transcript: "Sales 123", duration_seconds: 2 };
  expect(resolveSpeechRecording({ ...config, recording }, "Sales 123").kind).toBe("audio");
  expect(resolveSpeechRecording({ ...config, recording }, "Sales 456")).toMatchObject({ kind: "browser", code: "SPEECH_RECORDING_MISMATCH", recording: null });
  expect(resolveSpeechRecording({ ...config, recording, audio_asset_id: "replacement" }, "Sales 123").code).toBe("SPEECH_RECORDING_UNCONFIRMED");
  expect(resolveSpeechRecording({ ...config, recording, speech_source: "browser" }, "Sales 456").code).toBeNull();
  expect(resolveSpeechRecording({ ...config, speech_source: "video", speaking_asset_id: "voice", recording }, "Sales 123").kind).toBe("video");
});

test("rejects sensitive field naming variants including camelCase", () => {
  for (const field of ["phoneNumber", "emailAddress", "apiKey", "access_token"]) {
    expect(sensitiveSpeechField(field)).toBe(true);
  }
  expect(sensitiveSpeechField("telephone")).toBe(true);
  expect(sensitiveSpeechField("telemetry_count")).toBe(false);
});

test("selects the first matching prerecorded segment and reports unmatched conditions", () => {
  const recordings = [
    { asset_id: "low", sha256: "a".repeat(64), transcript: "较低", duration_seconds: 1, conditions: [{ variable: "sales", operator: "lt", value: 100 }] },
    { asset_id: "high", sha256: "b".repeat(64), transcript: "较高", duration_seconds: 1, conditions: [{ variable: "sales", operator: "gte", value: 100 }] },
  ] as const;
  const config = {
    ...defaultDigitalHumanConfig,
    speech_source: "audio" as const,
    recordings: recordings as unknown as Required<DigitalHumanSpec>["recordings"],
  };
  expect(resolveSpeechRecording(config, "较高", new Map([["sales", 120]])).recording?.asset_id).toBe("high");
  expect(resolveSpeechRecording(config, "未知", new Map([["sales", 1]])).code).toBe("SPEECH_RECORDING_MISMATCH");
  expect(resolveSpeechRecording(config, "未知", new Map()).code).toBe("SPEECH_RECORDING_CONDITION_UNMATCHED");
});

test("selects matching prerecorded segments by priority and stable asset id", () => {
  const config = {
    ...defaultDigitalHumanConfig,
    speech_source: "audio" as const,
    recordings: [
      { asset_id: "z-low", sha256: "a".repeat(64), transcript: "同一文案", duration_seconds: 1, priority: 1 },
      { asset_id: "a-tie", sha256: "b".repeat(64), transcript: "同一文案", duration_seconds: 1, priority: 5 },
      { asset_id: "a-high", sha256: "c".repeat(64), transcript: "同一文案", duration_seconds: 1, priority: 5 },
    ] as unknown as Required<DigitalHumanSpec>["recordings"],
  };
  expect(resolveSpeechRecording(config, "同一文案").recording?.asset_id).toBe("a-high");
});

test("consumes selected columns from multiple runtime results without querying", () => {
  const plan = buildSpeechPlan(speaker, idle, {
    sales: { status: "success", result, error: null, updatedAt: 1000 },
    states: { status: "success", result: { ...result, columns: [{ name: "status", data_type: "string" }], rows: [["ok"]] }, error: null, updatedAt: 2000 },
  });
  expect(plan.text).toBe("本月 1,234.5元，状态 正常");
  expect(plan.code).toBeNull();
  expect(plan.updatedAt).toBe(1000);
  expect(plan.values.has("region")).toBe(false);
});

test("isolates failed sources and does not read previous data while loading", () => {
  const loading = buildSpeechPlan(speaker, idle, {
    sales: { status: "loading", result, error: null },
  });
  expect(loading.loading).toBe(true);
  const failed = buildSpeechPlan(speaker, idle, {
    sales: { status: "error", result, error: new Error("internal secret") },
  });
  expect(failed.code).toBe("SPEECH_DATA_UNAVAILABLE");
  expect(failed.text).toBe("数据暂不可播报");
  expect(failed.text).not.toContain("internal secret");
});

test("rejects sensitive references, including aliases and prototype properties", () => {
  const denied = buildSpeechPlan({
    ...speaker,
    props: { speech_template: "{{value}}" },
    data_binding: { source: "components", variables: [{ name: "value", component_id: "sales", field: "access_token" }] },
  }, idle, { sales: { status: "success", result, error: null } });
  expect(denied.code).toBe("SPEECH_FIELD_DENIED");
  expect(() => parseSpeechTemplate("{{constructor}}")).toThrow();
});

test.each(["{{unclosed", "}}", "{{value | eval}}", "{{value + 1}}", '{{value | number:"0.000000000"}}', "{{value}}".repeat(51)])(
  "invalid syntax has an explicit fallback: %s", (template) => {
    expect(() => parseSpeechTemplate(template)).toThrow();
    expect(renderSpeechTemplate(template, result)).toBe("数据暂不可播报");
  },
);

test("supports Chinese field names and strict currency and number formatting", () => {
  expect(renderSpeechTemplate('{{销售额 | number:"+0.0"}}', {
    ...result, columns: [{ name: "销售额", data_type: "number" }], rows: [[1234.5]],
  })).toBe("+1,234.5");
  expect(parseSpeechTemplate('{{sales.value | number:"0.0a"}}')[0]?.option).toBe("0.0a");
});

  test("keeps nulls empty and distinguishes missing fields", () => {
  expect(renderSpeechTemplate("{{sales}}", { ...result, rows: [[null]] })).toBe("暂无数据");
  expect(renderSpeechTemplate("{{notBound}}", result)).toBe("字段不可用");
  });

  test("formats enum, rank, trend, and Chinese numbers", () => {
    const formatted = buildSpeechPlan({
      ...speaker,
      props: { speech_template: "{{state | enum}} {{sales.amount | rank}} {{sales.amount | trend}} {{sales.amount | number_zh}}" },
    }, idle, {
      sales: { status: "success", result: { ...result, columns: [{ name: "sales", data_type: "number" }], rows: [[1234]] }, error: null },
      states: { status: "success", result: { ...result, columns: [{ name: "status", data_type: "string" }], rows: [["ok"]] }, error: null },
    });
    expect(formatted.text).toContain("正常");
    expect(formatted.text).toContain("第1,234名");
    expect(formatted.text).toContain("上升");
    expect(formatted.text).toContain("一千二百三十四");
  });

test("evaluates all/any condition groups with scalar comparisons", () => {
  const values = new Map<string, QueryResult["rows"][number][number]>([
    ["sales", 120], ["status", "warning"],
  ]);
  expect(evaluateSpeechConditions([
    { variable: "sales", operator: "gte", value: 100 },
    { variable: "status", operator: "eq", value: "warning" },
  ], "all", values)).toBe(true);
  expect(evaluateSpeechConditions([
    { variable: "sales", operator: "lt", value: 100 },
    { variable: "status", operator: "eq", value: "warning" },
  ], "any", values)).toBe(true);
  expect(evaluateSpeechConditions([{ variable: "unknown", operator: "exists" }], "all", values)).toBe(false);
});

test("state transitions reject late speaking callbacks", () => {
  expect(canTransitionSpeechStatus("idle", "speaking")).toBe(false);
  expect(canTransitionSpeechStatus("queued", "preparing_media")).toBe(true);
  expect(canTransitionSpeechStatus("fallback", "speaking")).toBe(true);
  expect(canTransitionSpeechStatus("speaking", "idle")).toBe(true);
});

test("muting remains valid while data or media is still preparing", () => {
  expect(canTransitionSpeechStatus("disabled", "muted")).toBe(true);
  expect(canTransitionSpeechStatus("loading_data", "muted")).toBe(true);
  expect(canTransitionSpeechStatus("preparing_media", "muted")).toBe(true);
});

test("trigger windows support normal and cross-midnight ranges", () => {
  const morning = new Date("2026-01-01T10:30:00Z");
  const late = new Date("2026-01-01T23:30:00Z");
  const early = new Date("2026-01-02T01:30:00Z");
  expect(isWithinSpeechWindow("09:00", "18:00", "UTC", morning)).toBe(true);
  expect(isWithinSpeechWindow("09:00", "18:00", "UTC", late)).toBe(false);
  expect(isWithinSpeechWindow("22:00", "07:00", "UTC", late)).toBe(true);
  expect(isWithinSpeechWindow("22:00", "07:00", "UTC", early)).toBe(true);
  expect(isWithinSpeechWindow("22:00", "07:00", "UTC", morning)).toBe(false);
});
