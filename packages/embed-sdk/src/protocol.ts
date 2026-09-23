export type JsonValue =
  | null
  | boolean
  | number
  | string
  | JsonValue[]
  | { [key: string]: JsonValue };

export interface ReadyMessage {
  type: "ready";
  instance_id: string;
  protocol_version: 1;
  capabilities?: string[];
}

export type SpeechState = "disabled" | "idle" | "loading_data" | "ready" | "queued" | "preparing_media"
  | "speaking" | "paused" | "muted" | "waiting_gesture" | "fallback" | "error";

export type DigitalHumanCommand =
  | { component_id: string; action: "play" | "pause" | "stop" | "speak" | "getStatus" }
  | { component_id: string; action: "mute"; enabled: boolean }
  | { component_id: string; action: "setVolume"; volume: number };

export interface DigitalHumanState {
  component_id: string;
  status: SpeechState;
  code: string | null;
  muted: boolean;
  volume: number;
}

export type DigitalHumanEventName = "digitalHumanReady" | "statusChange" | "speechStart" | "speechEnd"
  | "speechError" | "fallback" | "userGestureRequired" | "subtitleCue";

export interface DigitalHumanEvent {
  name?: DigitalHumanEventName;
  outcome?: "completed" | "stopped" | "cancelled" | null;
  component_id: string;
  status: SpeechState;
  task_id: string | null;
  source: "initial" | "manual" | "interval" | "data_change" | "ranking_change" | "status_change" | "threshold" | "parameter" | "host";
  code: string | null;
  request_id: string;
  timestamp: number;
  cue_index?: number | null;
  cue_text?: string | null;
  cue_start?: number | null;
  cue_end?: number | null;
}

export interface DigitalHumanStatusMessage {
  type: "digitalHumanStatus";
  instance_id: string;
  request_id: string;
  state: DigitalHumanState;
}

export interface DigitalHumanEventMessage {
  type: "digitalHumanEvent";
  instance_id: string;
  event: DigitalHumanEvent;
}

export interface DigitalHumanMessage {
  type: "digitalHuman";
  instance_id: string;
  request_id: string;
  command: DigitalHumanCommand;
}

export interface RefreshMessage {
  type: "refresh";
  instance_id: string;
}

export interface SetParametersMessage {
  type: "setParameters";
  instance_id: string;
  request_id: string;
  parameters: Record<string, JsonValue>;
}

export interface GetParametersMessage {
  type: "getParameters";
  instance_id: string;
  request_id: string;
}

export interface ParametersMessage {
  type: "parameters";
  instance_id: string;
  request_id: string;
  parameters: Record<string, JsonValue>;
}

export interface FullscreenMessage {
  type: "fullscreen";
  instance_id: string;
  request_id: string;
  enabled: boolean;
}

export interface AckMessage {
  type: "ack";
  instance_id: string;
  request_id: string;
}

export interface ErrorMessage {
  type: "error";
  instance_id: string;
  request_id?: string | null;
  code: string;
  message: string;
}

export type HostMessage =
  | DigitalHumanMessage
  | RefreshMessage
  | SetParametersMessage
  | GetParametersMessage
  | FullscreenMessage;

export type PlayerMessage =
  | DigitalHumanStatusMessage
  | DigitalHumanEventMessage
  | ReadyMessage
  | ParametersMessage
  | AckMessage
  | ErrorMessage;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isJsonValue(value: unknown): value is JsonValue {
  if (
    value === null ||
    typeof value === "string" ||
    typeof value === "boolean"
  ) {
    return true;
  }
  if (typeof value === "number") {
    return Number.isFinite(value);
  }
  if (Array.isArray(value)) {
    return value.every(isJsonValue);
  }
  return isRecord(value) && Object.values(value).every(isJsonValue);
}

function isParameters(value: unknown): value is Record<string, JsonValue> {
  return isRecord(value) && Object.values(value).every(isJsonValue);
}

function isSpeechState(value: unknown): boolean {
  return typeof value === "string" && [
    "disabled", "idle", "loading_data", "ready", "queued", "preparing_media", "speaking",
    "paused", "muted", "waiting_gesture", "fallback", "error",
  ].includes(value);
}

export function isDigitalHumanCommand(value: unknown): value is DigitalHumanCommand {
  if (!isRecord(value) || typeof value.component_id !== "string" || !value.component_id.trim()) return false;
  if (Object.keys(value).some((key) => !["component_id", "action", "enabled", "volume"].includes(key))) return false;
  if (value.action === "mute") return typeof value.enabled === "boolean" && value.volume === undefined;
  if (value.action === "setVolume") {
    return value.enabled === undefined && typeof value.volume === "number" &&
      Number.isFinite(value.volume) && value.volume >= 0 && value.volume <= 1;
  }
  return typeof value.action === "string" && ["play", "pause", "stop", "speak", "getStatus"].includes(value.action) &&
    value.enabled === undefined && value.volume === undefined;
}

export function isPlayerMessage(value: unknown): value is PlayerMessage {
  if (
    !isRecord(value) ||
    typeof value.type !== "string" ||
    typeof value.instance_id !== "string"
  ) {
    return false;
  }
  if (value.type === "ready") {
    return value.protocol_version === 1 && (value.capabilities === undefined ||
      (Array.isArray(value.capabilities) && value.capabilities.every((item) => typeof item === "string")));
  }
  if (value.type === "digitalHumanStatus") {
    const state = value.state;
    return typeof value.request_id === "string" && isRecord(state) &&
      typeof state.component_id === "string" && isSpeechState(state.status) &&
      (state.code === null || typeof state.code === "string") &&
      typeof state.muted === "boolean" && typeof state.volume === "number" &&
      Number.isFinite(state.volume) && state.volume >= 0 && state.volume <= 1;
  }
  if (value.type === "digitalHumanEvent") {
    const event = value.event;
    if (!isRecord(event) || typeof event.component_id !== "string" || !isSpeechState(event.status)) return false;
    if (event.name !== undefined && !["digitalHumanReady", "statusChange", "speechStart", "speechEnd", "speechError", "fallback", "userGestureRequired", "subtitleCue"].includes(String(event.name))) return false;
    if (event.outcome !== undefined && event.outcome !== null && !["completed", "stopped", "cancelled"].includes(String(event.outcome))) return false;
    if (event.task_id !== null && typeof event.task_id !== "string") return false;
    if (typeof event.source !== "string" || !["initial", "manual", "interval", "data_change", "ranking_change", "status_change", "threshold", "parameter", "host"].includes(event.source)) return false;
    if ((event.code !== null && typeof event.code !== "string") || typeof event.request_id !== "string") return false;
    if (event.cue_index !== undefined && event.cue_index !== null && (typeof event.cue_index !== "number" || !Number.isInteger(event.cue_index) || event.cue_index < 0)) return false;
    if (event.cue_text !== undefined && event.cue_text !== null && typeof event.cue_text !== "string") return false;
    if (event.cue_start !== undefined && event.cue_start !== null && (typeof event.cue_start !== "number" || !Number.isFinite(event.cue_start) || event.cue_start < 0)) return false;
    if (event.cue_end !== undefined && event.cue_end !== null && (typeof event.cue_end !== "number" || !Number.isFinite(event.cue_end) || event.cue_end < 0)) return false;
    const cueValues = [event.cue_index, event.cue_text, event.cue_start, event.cue_end];
    const hasAnyCue = cueValues.some((value) => value !== undefined && value !== null);
    if (event.name === "subtitleCue" || hasAnyCue) {
      if (cueValues.some((value) => value === undefined || value === null)) return false;
      if ((event.cue_end as number) <= (event.cue_start as number)) return false;
    }
    return typeof event.timestamp === "number" && Number.isFinite(event.timestamp) && event.timestamp >= 0;
  }
  if (value.type === "ack") {
    return typeof value.request_id === "string";
  }
  if (value.type === "parameters") {
    return (
      typeof value.request_id === "string" &&
      isParameters(value.parameters)
    );
  }
  if (value.type === "error") {
    return (
      typeof value.code === "string" &&
      typeof value.message === "string" &&
      (value.request_id === undefined ||
        value.request_id === null ||
        typeof value.request_id === "string")
    );
  }
  return false;
}
