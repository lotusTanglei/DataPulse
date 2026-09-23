import {
  type AckMessage,
  type ErrorMessage,
  type HostMessage,
  isPlayerMessage,
  isDigitalHumanCommand,
  type JsonValue,
  type ParametersMessage,
  type DigitalHumanCommand,
  type DigitalHumanEvent,
  type DigitalHumanState,
  type DigitalHumanStatusMessage,
} from "./protocol";

const DEFAULT_REQUEST_TIMEOUT = 10_000;

export interface EmbedOptions {
  url: string;
  ticket: string;
  className?: string;
  requestTimeoutMs?: number;
  allowAudio?: boolean;
}

export interface DigitalHumanRequestOptions {
  signal?: AbortSignal;
}

export class EmbedError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "EmbedError";
    this.code = code;
  }
}

export interface EmbeddedScreen {
  readonly instanceId: string;
  readonly iframe: HTMLIFrameElement;
  readonly ready: boolean;
  refresh(): void;
  setParameters(values: Record<string, JsonValue>): Promise<void>;
  getParameters(): Promise<Record<string, JsonValue>>;
  fullscreen(enabled?: boolean): Promise<void>;
  digitalHuman(command: DigitalHumanCommand, options?: DigitalHumanRequestOptions): Promise<DigitalHumanState>;
  onDigitalHuman(listener: (event: DigitalHumanEvent) => void): () => void;
  onError(listener: (error: EmbedError) => void): () => void;
  destroy(): void;
}

interface PendingRequest {
  expected: "ack" | "parameters" | "digitalHumanStatus";
  resolve: (value: unknown) => void;
  reject: (error: EmbedError) => void;
  timeout: ReturnType<typeof setTimeout>;
  componentId?: string;
  cleanup: () => void;
}

function identifier(): string {
  return globalThis.crypto?.randomUUID?.() ??
    `datapulse-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function ensureEmbedUrl(value: string): URL {
  const url = new URL(value, window.location.href);
  if (!["http:", "https:"].includes(url.protocol)) {
    throw new TypeError("DataPulse embed URL must use HTTP or HTTPS.");
  }
  return url;
}

class EmbeddedScreenController implements EmbeddedScreen {
  readonly iframe: HTMLIFrameElement;
  readonly instanceId: string;

  private readonly origin: string;
  private readonly pending = new Map<string, PendingRequest>();
  private readonly errorListeners = new Set<(error: EmbedError) => void>();
  private readonly speechListeners = new Set<(event: DigitalHumanEvent) => void>();
  private readonly capabilities = new Set<string>();
  private readonly requestTimeoutMs: number;
  private destroyed = false;
  private isReady = false;
  private accessError: EmbedError | null = null;

  constructor(
    container: HTMLElement,
    options: EmbedOptions,
  ) {
    const url = ensureEmbedUrl(options.url);
    this.origin = url.origin;
    this.instanceId = identifier();
    this.requestTimeoutMs =
      options.requestTimeoutMs ?? DEFAULT_REQUEST_TIMEOUT;
    url.searchParams.set("ticket", options.ticket);
    url.searchParams.set("instance_id", this.instanceId);

    const iframe = document.createElement("iframe");
    iframe.src = url.toString();
    iframe.title = "DataPulse embedded screen";
    iframe.referrerPolicy = "no-referrer";
    iframe.allow = options.allowAudio ? "fullscreen; autoplay" : "fullscreen";
    iframe.setAttribute("allowfullscreen", "");
    iframe.setAttribute("sandbox", "allow-scripts allow-same-origin");
    if (options.className) {
      iframe.className = options.className;
    }
    this.iframe = iframe;
    window.addEventListener("message", this.handleMessage);
    container.append(iframe);
  }

  get ready(): boolean {
    return this.isReady;
  }

  refresh(): void {
    this.post({
      type: "refresh",
      instance_id: this.instanceId,
    });
  }

  setParameters(values: Record<string, JsonValue>): Promise<void> {
    return this.request<void>("ack", {
      type: "setParameters",
      instance_id: this.instanceId,
      request_id: identifier(),
      parameters: structuredClone(values),
    });
  }

  getParameters(): Promise<Record<string, JsonValue>> {
    return this.request<Record<string, JsonValue>>("parameters", {
      type: "getParameters",
      instance_id: this.instanceId,
      request_id: identifier(),
    });
  }

  fullscreen(enabled = true): Promise<void> {
    return this.request<void>("ack", {
      type: "fullscreen",
      instance_id: this.instanceId,
      request_id: identifier(),
      enabled,
    });
  }

  onError(listener: (error: EmbedError) => void): () => void {
    this.errorListeners.add(listener);
    return () => this.errorListeners.delete(listener);
  }

  digitalHuman(command: DigitalHumanCommand, options?: DigitalHumanRequestOptions): Promise<DigitalHumanState> {
    if (this.destroyed) return Promise.reject(new EmbedError("EMBED_DESTROYED", "The embedded screen was destroyed."));
    if (this.accessError) return Promise.reject(this.accessError);
    if (!this.isReady) return Promise.reject(new EmbedError("EMBED_PLAYER_NOT_READY", "The embedded screen is not ready."));
    if (!this.capabilities.has("digitalHuman.v1")) {
      return Promise.reject(new EmbedError("EMBED_CAPABILITY_UNAVAILABLE", "Digital human controls are unavailable."));
    }
    if (!isDigitalHumanCommand(command)) {
      return Promise.reject(new EmbedError("DIGITAL_HUMAN_COMMAND_INVALID", "Invalid digital human command."));
    }
    return this.request<DigitalHumanState>("digitalHumanStatus", {
      type: "digitalHuman", instance_id: this.instanceId, request_id: identifier(),
      command: structuredClone(command),
    }, options?.signal);
  }

  onDigitalHuman(listener: (event: DigitalHumanEvent) => void): () => void {
    this.speechListeners.add(listener);
    return () => this.speechListeners.delete(listener);
  }

  destroy(): void {
    if (this.destroyed) {
      return;
    }
    this.destroyed = true;
    this.isReady = false;
    window.removeEventListener("message", this.handleMessage);
    const error = new EmbedError(
      "EMBED_DESTROYED",
      "The embedded screen was destroyed.",
    );
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timeout);
      pending.cleanup();
      pending.reject(error);
    }
    this.pending.clear();
    this.errorListeners.clear();
    this.speechListeners.clear();
    this.iframe.remove();
  }

  private post(message: HostMessage): void {
    if (this.destroyed) {
      throw new EmbedError(
        "EMBED_DESTROYED",
        "The embedded screen was destroyed.",
      );
    }
    if (this.accessError) throw this.accessError;
    this.iframe.contentWindow?.postMessage(message, this.origin);
  }

  private request<T>(
    expected: PendingRequest["expected"],
    message: Exclude<HostMessage, { type: "refresh" }>,
    signal?: AbortSignal,
  ): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      const cancelled = () => new EmbedError("EMBED_REQUEST_CANCELLED", "The embed request was cancelled.");
      if (signal?.aborted) {
        reject(cancelled());
        return;
      }
      const onAbort = () => this.removePending(message.request_id)?.reject(cancelled());
      const timeout = setTimeout(() => {
        this.removePending(message.request_id);
        reject(
          new EmbedError(
            "EMBED_REQUEST_TIMEOUT",
            "The embedded screen did not respond in time.",
          ),
        );
      }, this.requestTimeoutMs);
      this.pending.set(message.request_id, {
        expected,
        resolve: (value) => resolve(value as T),
        reject,
        timeout,
        componentId: message.type === "digitalHuman" ? message.command.component_id : undefined,
        cleanup: () => signal?.removeEventListener("abort", onAbort),
      });
      signal?.addEventListener("abort", onAbort, { once: true });
      try {
        this.post(message);
      } catch (error) {
        this.removePending(message.request_id);
        reject(
          error instanceof EmbedError
            ? error
            : new EmbedError("EMBED_REQUEST_FAILED", String(error)),
        );
      }
    });
  }

  private removePending(requestId: string): PendingRequest | undefined {
    const pending = this.pending.get(requestId);
    if (pending) {
      clearTimeout(pending.timeout);
      pending.cleanup();
      this.pending.delete(requestId);
    }
    return pending;
  }

  private readonly handleMessage = (event: MessageEvent<unknown>): void => {
    if (
      this.destroyed ||
      event.origin !== this.origin ||
      event.source !== this.iframe.contentWindow ||
      !isPlayerMessage(event.data) ||
      event.data.instance_id !== this.instanceId
    ) {
      return;
    }
    const message = event.data;
    if (message.type === "ready") {
      if (this.accessError) return;
      this.isReady = true;
      this.capabilities.clear();
      for (const capability of message.capabilities ?? []) this.capabilities.add(capability);
      return;
    }
    if (message.type === "digitalHumanEvent") {
      if (this.accessError) return;
      for (const listener of this.speechListeners) listener(structuredClone(message.event));
      return;
    }
    if (message.type === "error") {
      this.handleError(message);
      return;
    }
    this.resolveRequest(message);
  };

  private handleError(message: ErrorMessage): void {
    const error = new EmbedError(message.code, message.message);
    if (["EMBED_TICKET_EXPIRED", "EMBED_TICKET_INVALID", "EMBED_AUTH_REQUIRED", "EMBED_ORIGIN_DENIED", "EMBED_ADDRESS_DENIED", "EMBED_SCREEN_UNAVAILABLE"].includes(error.code)) {
      this.accessError = error;
      this.isReady = false;
      this.capabilities.clear();
      for (const requestId of this.pending.keys()) this.removePending(requestId)?.reject(error);
    }
    if (message.request_id) {
      const pending = this.removePending(message.request_id);
      if (pending) {
        pending.reject(error);
      }
    }
    for (const listener of this.errorListeners) {
      listener(error);
    }
  }

  private resolveRequest(message: AckMessage | ParametersMessage | DigitalHumanStatusMessage): void {
    const pending = this.pending.get(message.request_id);
    if (!pending || pending.expected !== message.type) {
      return;
    }
    if (message.type === "digitalHumanStatus" && message.state.component_id !== pending.componentId) return;
    this.removePending(message.request_id);
    pending.resolve(
      message.type === "parameters"
        ? structuredClone(message.parameters)
        : message.type === "digitalHumanStatus" ? structuredClone(message.state)
        : undefined,
    );
  }
}

export const DataPulseEmbed = {
  mount(container: HTMLElement, options: EmbedOptions): EmbeddedScreen {
    return new EmbeddedScreenController(container, options);
  },
};

export type { JsonValue } from "./protocol";
export type { DigitalHumanCommand, DigitalHumanEvent, DigitalHumanState } from "./protocol";
