import type { JsonValue } from "../query/types";

interface BridgeOptions {
  allowedOrigin: string;
  instanceId: string;
  refresh: () => void | Promise<void>;
  setParameters: (
    parameters: Record<string, JsonValue>,
  ) => void | Promise<void>;
  getParameters: () =>
    | Record<string, JsonValue>
    | Promise<Record<string, JsonValue>>;
  fullscreen: (enabled: boolean) => void | Promise<void>;
}

interface HostMessage {
  type: "refresh" | "setParameters" | "getParameters" | "fullscreen";
  instance_id: string;
  request_id?: string;
  parameters?: Record<string, JsonValue>;
  enabled?: boolean;
}

export interface EmbedBridge {
  ready(): void;
  reportError(error: unknown): void;
  destroy(): void;
}

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

function isHostMessage(value: unknown): value is HostMessage {
  if (
    !isRecord(value) ||
    typeof value.instance_id !== "string" ||
    typeof value.type !== "string"
  ) {
    return false;
  }
  if (value.type === "refresh") {
    return true;
  }
  if (value.type === "getParameters") {
    return typeof value.request_id === "string";
  }
  if (value.type === "setParameters") {
    return (
      typeof value.request_id === "string" &&
      isParameters(value.parameters)
    );
  }
  if (value.type === "fullscreen") {
    return (
      typeof value.request_id === "string" &&
      typeof value.enabled === "boolean"
    );
  }
  return false;
}

function errorDetails(error: unknown): { code: string; message: string } {
  if (error instanceof Error) {
    const code =
      "code" in error && typeof error.code === "string"
        ? error.code
        : "EMBED_PLAYER_ERROR";
    return { code, message: error.message || "Embedded player error." };
  }
  return {
    code: "EMBED_PLAYER_ERROR",
    message: "Embedded player error.",
  };
}

export function createEmbedBridge(options: BridgeOptions): EmbedBridge {
  let destroyed = false;

  function post(message: Record<string, unknown>): void {
    if (!destroyed) {
      window.parent.postMessage(
        {
          ...message,
          instance_id: options.instanceId,
        },
        options.allowedOrigin,
      );
    }
  }

  function replyError(error: unknown, requestId?: string): void {
    post({
      type: "error",
      ...(requestId === undefined ? {} : { request_id: requestId }),
      ...errorDetails(error),
    });
  }

  async function handle(message: HostMessage): Promise<void> {
    if (message.type === "refresh") {
      try {
        await options.refresh();
      } catch (error) {
        replyError(error);
      }
      return;
    }
    try {
      if (message.type === "setParameters") {
        await options.setParameters(message.parameters!);
        post({ type: "ack", request_id: message.request_id });
      } else if (message.type === "getParameters") {
        post({
          type: "parameters",
          request_id: message.request_id,
          parameters: await options.getParameters(),
        });
      } else {
        await options.fullscreen(message.enabled!);
        post({ type: "ack", request_id: message.request_id });
      }
    } catch (error) {
      replyError(error, message.request_id);
    }
  }

  const receive = (event: MessageEvent<unknown>): void => {
    if (
      destroyed ||
      event.origin !== options.allowedOrigin ||
      event.source !== window.parent ||
      !isHostMessage(event.data) ||
      event.data.instance_id !== options.instanceId
    ) {
      return;
    }
    void handle(event.data);
  };
  window.addEventListener("message", receive);

  return {
    ready() {
      post({ type: "ready", protocol_version: 1 });
    },
    reportError(error) {
      replyError(error);
    },
    destroy() {
      if (!destroyed) {
        destroyed = true;
        window.removeEventListener("message", receive);
      }
    },
  };
}
