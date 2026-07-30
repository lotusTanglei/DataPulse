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
  | RefreshMessage
  | SetParametersMessage
  | GetParametersMessage
  | FullscreenMessage;

export type PlayerMessage =
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

export function isPlayerMessage(value: unknown): value is PlayerMessage {
  if (
    !isRecord(value) ||
    typeof value.type !== "string" ||
    typeof value.instance_id !== "string"
  ) {
    return false;
  }
  if (value.type === "ready") {
    return value.protocol_version === 1;
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
