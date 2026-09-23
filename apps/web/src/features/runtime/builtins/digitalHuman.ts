import type { DigitalHumanBinding, DigitalHumanSpec, DigitalHumanTrigger } from "@datapulse/schema";
import type { JsonValue, QueryResult } from "../../query/types";
import type { ComponentInstance, ComponentQueryState } from "../types";

export type DigitalHumanStatus = "disabled" | "idle" | "loading_data" | "ready" | "queued"
  | "preparing_media" | "speaking" | "paused" | "muted" | "waiting_gesture" | "fallback" | "error";
export type SpeechSource = "initial" | "manual" | "interval" | "data_change" | "ranking_change" | "status_change" | "threshold" | "parameter" | "host";

export const defaultSpeechTrigger: Required<DigitalHumanTrigger> = {
  kind: "data_change", interval_seconds: null, cooldown_seconds: 30, min_change: 0,
  variable: null, threshold: null, direction: "above", edge: "enter", parameter: null, include_host: true,
  conditions: [], condition_mode: "all", priority: 0, debounce_seconds: 0, window_start: null, window_end: null,
};

const speechTransitions: Record<DigitalHumanStatus, readonly DigitalHumanStatus[]> = {
  disabled: ["idle", "loading_data", "muted"],
  idle: ["disabled", "loading_data", "ready", "queued", "muted", "fallback", "preparing_media"],
  loading_data: ["disabled", "idle", "ready", "muted", "fallback", "preparing_media"],
  ready: ["disabled", "idle", "loading_data", "queued", "muted", "fallback", "preparing_media"],
  queued: ["disabled", "idle", "muted", "fallback", "preparing_media"],
  preparing_media: ["disabled", "idle", "muted", "speaking", "paused", "fallback", "waiting_gesture", "error"],
  speaking: ["disabled", "idle", "muted", "paused", "fallback", "error"],
  paused: ["disabled", "idle", "muted", "speaking", "fallback", "error"],
  muted: ["disabled", "idle", "ready", "loading_data", "queued", "fallback", "preparing_media"],
  waiting_gesture: ["disabled", "idle", "muted", "ready", "preparing_media", "speaking", "fallback", "error"],
  fallback: ["disabled", "idle", "ready", "muted", "queued", "preparing_media", "speaking", "error"],
  error: ["disabled", "idle", "ready", "muted", "fallback", "preparing_media"],
};

export function canTransitionSpeechStatus(from: DigitalHumanStatus, to: DigitalHumanStatus): boolean {
  return from === to || speechTransitions[from].includes(to);
}

export function isWithinSpeechWindow(
  start: string | null | undefined,
  end: string | null | undefined,
  timezone: string,
  now: Date = new Date(),
): boolean {
  if (!start || !end) return true;
  const time = new Intl.DateTimeFormat("en-GB", {
    timeZone: timezone, hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).format(now);
  return start <= end ? time >= start && time < end : time >= start || time < end;
}

export const defaultDigitalHumanConfig: Required<DigitalHumanSpec> = {
  schema_version: 1, enabled: true, name: "DataPulse 数字人", role: "数据播报员",
  avatar_asset_id: "", speaking_asset_id: "", audio_asset_id: "",
  speech_source: "auto", recording: null, recordings: [], actions: [],
  speech_segments: [],
  avatar_kind: "image", speaking_kind: "image", fit: "contain", mirror: false,
  show_identity: true, show_status: true, show_controls: true, animation: true,
  speech_template: "数据播报：{{value}}", language: "zh-CN", timezone: "Asia/Shanghai",
  empty_text: "暂无数据", missing_text: "字段不可用", error_text: "数据暂不可播报", stale_text: "数据已过期",
  stale_after_seconds: 300, rate: 1, pitch: 1, volume: 1, auto_play: true, voice_enabled: true,
  subtitle_enabled: true, subtitle_position: "bottom", subtitle_color: "#FFFFFF", subtitle_background: "#000000B8", subtitle_scroll: "wrap", subtitle_font_size: 20, subtitle_max_lines: 3,
  muted: true, trigger: defaultSpeechTrigger, queue_policy: "merge", max_duration_seconds: 30,
  max_queue_length: 5, task_ttl_seconds: 60, daily_max_count: 1000, daily_max_seconds: 7200,
  quiet_start: null, quiet_end: null, quiet_mode: "mute",
};

export function digitalHumanConfig(instance: ComponentInstance): Required<DigitalHumanSpec> {
  const config = instance.props as DigitalHumanSpec | undefined;
  const speechSegments = (config?.speech_segments ?? []).map((segment) => ({
    kind: segment.kind ?? "paragraph",
    text: segment.text ?? "",
    duration_ms: segment.duration_ms ?? 500,
  }));
  return { ...defaultDigitalHumanConfig, ...config, speech_segments: speechSegments, trigger: { ...defaultSpeechTrigger, ...config?.trigger } };
}

type SpeechCondition = NonNullable<DigitalHumanTrigger["conditions"]>[number];

function comparable(value: JsonValue): string | number | boolean | null {
  if (value === null || typeof value === "string" || typeof value === "number" || typeof value === "boolean") return value;
  return null;
}

function conditionResult(condition: SpeechCondition, values: Map<string, JsonValue>): boolean {
  const actual = values.get(condition.variable);
  if (condition.operator === "exists") return actual !== undefined && actual !== null;
  if (actual === undefined || actual === null) return false;
  const left = comparable(actual);
  const right = comparable(condition.value ?? null);
  if (left === null || right === null) return false;
  if (condition.operator === "eq") return String(left) === String(right);
  if (condition.operator === "neq") return String(left) !== String(right);
  const numericLeft = typeof left === "number" ? left : Number(left);
  const numericRight = typeof right === "number" ? right : Number(right);
  if (!Number.isFinite(numericLeft) || !Number.isFinite(numericRight)) return false;
  if (condition.operator === "gt") return numericLeft > numericRight;
  if (condition.operator === "gte") return numericLeft >= numericRight;
  if (condition.operator === "lt") return numericLeft < numericRight;
  return numericLeft <= numericRight;
}

export function evaluateSpeechConditions(
  conditions: readonly SpeechCondition[],
  mode: "all" | "any",
  values: Map<string, JsonValue>,
): boolean {
  if (!conditions.length) return false;
  return mode === "any"
    ? conditions.some((condition) => conditionResult(condition, values))
    : conditions.every((condition) => conditionResult(condition, values));
}

export function resolveSpeechRecording(
  config: Required<DigitalHumanSpec>,
  text: string,
  values: Map<string, JsonValue> = new Map(),
) {
  const kind = config.speech_source === "video" ? "video" : "audio";
  const candidates = [
    ...config.recordings,
    ...(config.recording && !config.recordings.some((item) => item.asset_id === config.recording?.asset_id)
      ? [config.recording]
      : []),
  ].sort((left, right) =>
    (right.priority ?? 0) - (left.priority ?? 0) || left.asset_id.localeCompare(right.asset_id),
  );
  const selected = candidates.find((item) => !item.conditions?.length || evaluateSpeechConditions(
    item.conditions ?? [],
    item.condition_mode ?? "all",
    values,
  ));
  const hasMappedCandidates = config.recordings.length > 0;
  const configuredAssetId = kind === "video" ? config.speaking_asset_id : config.audio_asset_id;
  const assetId = hasMappedCandidates
    ? selected?.asset_id ?? ""
    : configuredAssetId;
  if (hasMappedCandidates && !selected) {
    return { kind: "browser" as const, recording: null, code: "SPEECH_RECORDING_CONDITION_UNMATCHED" };
  }
  if (config.speech_source === "browser" || (config.speech_source === "auto" && !assetId)) {
    return { kind: "browser" as const, recording: null, code: null };
  }
  const recording = selected ?? null;
  const normalize = (value: string) => value.trim().replace(/\s+/g, " ");
  const code = !assetId ? "SPEECH_ASSET_UNAVAILABLE"
    : !recording || recording.asset_id !== assetId ? "SPEECH_RECORDING_UNCONFIRMED"
    : normalize(recording.transcript) !== normalize(text) ? "SPEECH_RECORDING_MISMATCH" : null;
  return code ? { kind: "browser" as const, recording: null, code } : { kind, recording, code };
}

interface Placeholder {
  start: number;
  end: number;
  name: string;
  format: string;
  option?: string;
}

export function parseSpeechTemplate(template: string): Placeholder[] {
  if (!template.trim() || [...template].length > 4000) throw new Error("话术长度应为 1 到 4000 字符。");
  const tokens: Placeholder[] = [];
  let offset = 0;
  while (offset < template.length) {
    const start = template.indexOf("{{", offset);
    const closing = template.indexOf("}}", offset);
    if (start < 0) {
      if (closing >= 0) throw new Error("话术变量的结束标记多余。");
      break;
    }
    if (closing < start) throw new Error("话术变量未闭合。");
    const match = /^([\p{L}\p{N}_.-]+)(?:\s*\|\s*(number|percent|currency|date|enum|rank|trend|number_zh|text)(?:\s*:\s*"([^"{}\r\n]{1,32})")?)?$/u
      .exec(template.slice(start + 2, closing).trim());
    if (!match) throw new Error("话术变量或格式无效。");
    const name = match[1]!;
    const format = match[2] ?? "text";
    const option = match[3];
    if (name.split(".").some((part) => ["__proto__", "constructor", "prototype"].includes(part))) {
      throw new Error("话术变量名称无效。");
    }
    if (["number", "percent"].includes(format) && option && !/^\+?0(?:\.0{1,8})?a?$/.test(option)) {
      throw new Error("数字格式无效。");
    }
    if (format === "currency" && option && !/^[A-Z]{3}$/.test(option)) throw new Error("货币代码无效。");
    if (format === "date" && option && !["date", "time", "datetime"].includes(option)) throw new Error("日期格式无效。");
    if (["enum", "rank", "trend", "number_zh", "text"].includes(format) && option) throw new Error("该格式不接受参数。");
    tokens.push({ start, end: closing + 2, name, format, option });
    if (tokens.length > 50) throw new Error("话术最多包含 50 个变量。");
    offset = closing + 2;
  }
  return tokens;
}

export function sensitiveSpeechField(name: string): boolean {
  const normalized = name.replace(/([a-z0-9])([A-Z])/g, "$1_$2");
  if (/(?:身份证|手机号|电话|邮箱)/u.test(normalized)) return true;
  return /(?:^|[^a-z0-9])(?:password|passwd|secret|token|api[_-]?key|credential|phone|mobile|telephone|tel|email|ssn)(?:$|[^a-z0-9])/i.test(normalized);
}

export interface SpeechPlan {
  text: string;
  values: Map<string, JsonValue>;
  code: string | null;
  requestId: string;
  loading: boolean;
  fingerprint: string;
  updatedAt: number | null;
}

function chineseNumber(value: number): string {
  if (!Number.isFinite(value)) return "";
  if (value === 0) return "零";
  const digits = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九"];
  const units = ["", "十", "百", "千"];
  const groups = ["", "万", "亿", "兆"];
  const integer = Math.trunc(Math.abs(value));
  const renderGroup = (group: number): string => {
    let output = "";
    let zero = false;
    for (let index = 3; index >= 0; index -= 1) {
      const digit = Math.floor(group / 10 ** index) % 10;
      if (digit === 0) { if (output) zero = true; continue; }
      if (zero) output += "零";
      output += digits[digit] + units[index];
      zero = false;
    }
    return output;
  };
  const chunks: string[] = [];
  let remaining = integer;
  while (remaining > 0) { chunks.unshift(String(remaining % 10000).padStart(4, "0")); remaining = Math.floor(remaining / 10000); }
  let output = "";
  chunks.forEach((chunk, index) => {
    const group = Number(chunk);
    if (group === 0) return;
    if (output && group < 1000) output += "零";
    output += renderGroup(group) + groups[chunks.length - index - 1];
  });
  if (integer < 20 && output.startsWith("一十")) output = output.slice(1);
  if (value < 0) output = "负" + output;
  const fraction = Math.abs(value) % 1;
  if (fraction > 0) {
    output += "点";
    for (const digit of fraction.toFixed(8).slice(2).replace(/0+$/, "")) output += digits[Number(digit)];
  }
  return output;
}

function formatted(value: JsonValue, token: Placeholder, config: Required<DigitalHumanSpec>): string {
  if (value === null) return config.empty_text;
  if (typeof value === "object") return config.missing_text;
  if (token.format === "number_zh") {
    const numeric = typeof value === "number" ? value : typeof value === "string" ? Number(value) : NaN;
    return Number.isFinite(numeric) ? chineseNumber(numeric) : config.missing_text;
  }
  if (token.format === "rank") {
    const numeric = typeof value === "number" ? value : typeof value === "string" ? Number(value) : NaN;
    return Number.isFinite(numeric) ? `第${new Intl.NumberFormat(config.language).format(numeric)}名` : config.missing_text;
  }
  if (token.format === "trend") {
    const numeric = typeof value === "number" ? value : typeof value === "string" ? Number(value) : NaN;
    if (!Number.isFinite(numeric)) return config.missing_text;
    return numeric > 0 ? "上升" : numeric < 0 ? "下降" : "持平";
  }
  if (["number", "percent", "currency"].includes(token.format)) {
    const numeric = typeof value === "number" ? value : typeof value === "string" && value.trim() ? Number(value) : NaN;
    if (!Number.isFinite(numeric)) return config.missing_text;
    const precision = token.option?.match(/\.([0]+)/)?.[1]?.length;
    return new Intl.NumberFormat(config.language, {
      style: token.format === "currency" ? "currency" : token.format === "percent" ? "percent" : "decimal",
      ...(token.format === "currency" ? { currency: token.option ?? "CNY" } : {}),
      ...(token.option?.endsWith("a") ? { notation: "compact" } : {}),
      ...(token.option?.startsWith("+") ? { signDisplay: "exceptZero" } : {}),
      minimumFractionDigits: precision ?? (token.format === "percent" ? 1 : 0),
      maximumFractionDigits: precision ?? (token.format === "percent" ? 1 : 2),
    }).format(numeric);
  }
  if (token.format === "date") {
    const date = typeof value === "string" ? new Date(value) : null;
    if (!date || !Number.isFinite(date.getTime())) return config.missing_text;
    return new Intl.DateTimeFormat(config.language, {
      timeZone: config.timezone,
      ...(token.option !== "time" ? { dateStyle: "medium" } : {}),
      ...(token.option === "time" || token.option === "datetime" ? { timeStyle: "short" } : {}),
    }).format(date);
  }
  return String(value).slice(0, 500);
}

export function buildSpeechPlan(
  instance: ComponentInstance,
  ownState: ComponentQueryState,
  states: Record<string, ComponentQueryState> = {},
): SpeechPlan {
  const config = digitalHumanConfig(instance);
  const values = new Map<string, JsonValue>();
  const units = new Map<string, string>();
  const labels = new Map<string, Record<string, string>>();
  let code: string | null = null;
  let requestId = ownState.result?.request_id ?? "";
  let loading = ownState.status === "loading";
  const updateTimes: number[] = [];
  if (ownState.updatedAt !== undefined) updateTimes.push(ownState.updatedAt);
  const missing = new Set<string>();
  const binding = instance.data_binding;
  if (binding?.source === "components") {
    for (const variable of (binding as unknown as DigitalHumanBinding).variables ?? []) {
      const state = states[variable.component_id];
      loading ||= state?.status === "loading" || state?.status === "idle";
      const result = state?.result;
      if (state?.updatedAt !== undefined) updateTimes.push(state.updatedAt);
      requestId = result?.request_id ?? requestId;
      if (!state || state.status === "error") {
        code = "SPEECH_DATA_UNAVAILABLE";
        continue;
      }
      if (sensitiveSpeechField(variable.field) || sensitiveSpeechField(variable.name)) {
        code = "SPEECH_FIELD_DENIED";
        continue;
      }
      const index = result?.columns.findIndex((column) => column.name === variable.field) ?? -1;
      if (index < 0) missing.add(variable.name);
      values.set(variable.name, result?.rows[variable.row ?? 0]?.[index] ?? null);
      units.set(variable.name, variable.unit ?? "");
      labels.set(variable.name, variable.enum_labels ?? {});
    }
  } else {
    const result = ownState.result;
    if (ownState.status === "error") code = "SPEECH_DATA_UNAVAILABLE";
    for (const [index, column] of (result?.columns ?? []).entries()) {
      if (!sensitiveSpeechField(column.name)) values.set(column.name, result?.rows[0]?.[index] ?? null);
    }
    const first = result?.columns[0];
    if (first && !sensitiveSpeechField(first.name) && !values.has("value")) {
      values.set("value", result?.rows[0]?.[0] ?? null);
    }
  }
  let text = config.error_text;
  try {
    if (!code) {
      text = "";
      const segments = config.speech_segments.length
        ? config.speech_segments
        : [{ kind: "paragraph" as const, text: config.speech_template, duration_ms: 500 }];
      let needsSeparator = false;
      for (const segment of segments) {
        if (segment.kind === "pause") {
          needsSeparator = text.length > 0;
          continue;
        }
        const rendered = renderSpeechText(segment.text ?? "", config, values, units, labels, missing);
        if (rendered.code === "SPEECH_FIELD_DENIED") {
          code = rendered.code;
          text = config.error_text;
          break;
        }
        if (rendered.code && !code) code = rendered.code;
        if (needsSeparator && text) text += "\n";
        text += rendered.text;
        needsSeparator = true;
      }
    }
    if ([...text].length > 4000) {
      code = "SPEECH_TEXT_TOO_LONG";
      text = config.error_text;
    }
  } catch {
    code = "SPEECH_TEMPLATE_INVALID";
    text = config.error_text;
  }
  return {
    text, code, requestId, values, loading, fingerprint: JSON.stringify([...values]),
    updatedAt: updateTimes.length ? Math.min(...updateTimes) : null,
  };
}

function renderSpeechText(
  template: string,
  config: Required<DigitalHumanSpec>,
  values: Map<string, JsonValue>,
  units: Map<string, string>,
  labels: Map<string, Record<string, string>>,
  missing: Set<string>,
): { text: string; code: string | null } {
  const tokens = parseSpeechTemplate(template);
  let offset = 0;
  let text = "";
  let code: string | null = null;
  for (const token of tokens) {
    text += template.slice(offset, token.start);
    if (sensitiveSpeechField(token.name)) return { text: config.error_text, code: "SPEECH_FIELD_DENIED" };
    const value = values.get(token.name);
    if (value === undefined || missing.has(token.name)) {
      text += config.missing_text;
      code = "SPEECH_FIELD_MISSING";
    } else {
      const mapping = labels.get(token.name);
      text += mapping && Object.hasOwn(mapping, String(value))
        ? mapping[String(value)]!
        : formatted(value, token, config) + (value === null ? "" : units.get(token.name) ?? "");
    }
    offset = token.end;
  }
  text += template.slice(offset);
  return { text, code };
}

export function renderSpeechTemplate(template: string, result: QueryResult | null): string {
  return buildSpeechPlan(
    { id: "preview", type: "builtin.digital_human", frame: { x: 0, y: 0, width: 320, height: 420 }, props: { speech_template: template } },
    { result, status: result ? "success" : "idle", error: null },
  ).text;
}

export function resultFingerprint(result: QueryResult | null): string {
  if (!result) return "empty";
  return JSON.stringify({ columns: result.columns, rows: result.rows });
}
