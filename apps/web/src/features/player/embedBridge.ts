import type { JsonValue } from "../query/types";
import { isSpeechCommand, type SpeechCommand, type SpeechEvent, type SpeechStatus } from "../runtime/speechProtocol";

interface BridgeOptions {
  allowedOrigin: string;
  instanceId: string;
  checkAccess?: () => void;
  refresh: () => void | Promise<void>;
  setParameters: (
    parameters: Record<string, JsonValue>,
  ) => void | Promise<void>;
  getParameters: () =>
    | Record<string, JsonValue>
    | Promise<Record<string, JsonValue>>;
  fullscreen: (enabled: boolean) => void | Promise<void>;
  speechCommand?: (command: SpeechCommand) => SpeechStatus | Promise<SpeechStatus>;
}

interface HostMessage {
  type: "refresh" | "setParameters" | "getParameters" | "fullscreen" | "digitalHuman";
  instance_id: string;
  request_id?: string;
  parameters?: Record<string, JsonValue>;
  enabled?: boolean;
  command?: SpeechCommand;
}

export interface EmbedBridge {
  ready(): void;
  reportError(error: unknown): void;
  reportSpeechEvent(event: SpeechEvent): void;
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
  if (value.type === "digitalHuman") {
    return typeof value.request_id === "string" && isSpeechCommand(value.command);
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
  let announcedReady = false;
  const initialSpeechEvents: SpeechEvent[] = [];

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
    try {
      options.checkAccess?.();
    } catch (error) {
      replyError(error, message.request_id);
      return;
    }
    if (message.type === "refresh") {
      try {
        await options.refresh();
      } catch (error) {
        replyError(error);
      }
      return;
    }
    try {
      if (message.type === "digitalHuman") {
        if (!options.speechCommand) {
          throw Object.assign(new Error("Digital human is not configured."), { code: "DIGITAL_HUMAN_NOT_CONFIGURED" });
        }
        post({ type: "digitalHumanStatus", request_id: message.request_id, state: await options.speechCommand(message.command!) });
      } else if (message.type === "setParameters") {
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
      !isRecord(event.data) ||
      event.data.instance_id !== options.instanceId
    ) {
      return;
    }
    if (!isHostMessage(event.data)) {
      if (event.data.type === "digitalHuman" && typeof event.data.request_id === "string" && event.data.request_id.trim()) {
        replyError(Object.assign(new Error("Invalid digital human command."), {
          code: "DIGITAL_HUMAN_COMMAND_INVALID",
        }), event.data.request_id);
      }
      return;
    }
    void handle(event.data);
  };
  window.addEventListener("message", receive);

  return {
    ready() {
      if (destroyed || announcedReady) return;
      announcedReady = true;
      post({ type: "ready", protocol_version: 1, ...(options.speechCommand ? { capabilities: ["digitalHuman.v1"] } : {}) });
      for (const event of initialSpeechEvents.splice(0)) post({ type: "digitalHumanEvent", event });
    },
    reportError(error) {
      replyError(error);
    },
    reportSpeechEvent(event) {
      if (destroyed) return;
      if (!announcedReady) {
        if (initialSpeechEvents.length >= 512) initialSpeechEvents.shift();
        initialSpeechEvents.push(structuredClone(event));
        return;
      }
      post({ type: "digitalHumanEvent", event });
    },
    destroy() {
      if (!destroyed) {
        destroyed = true;
        initialSpeechEvents.length = 0;
        window.removeEventListener("message", receive);
      }
    },
  };
}
