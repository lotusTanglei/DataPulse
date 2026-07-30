import {
  type AckMessage,
  type ErrorMessage,
  type HostMessage,
  isPlayerMessage,
  type JsonValue,
  type ParametersMessage,
} from "./protocol";

const DEFAULT_REQUEST_TIMEOUT = 10_000;

export interface EmbedOptions {
  url: string;
  ticket: string;
  className?: string;
  requestTimeoutMs?: number;
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
  onError(listener: (error: EmbedError) => void): () => void;
  destroy(): void;
}

interface PendingRequest {
  expected: "ack" | "parameters";
  resolve: (value: unknown) => void;
  reject: (error: EmbedError) => void;
  timeout: ReturnType<typeof setTimeout>;
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
  private readonly requestTimeoutMs: number;
  private destroyed = false;
  private isReady = false;

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
    iframe.allow = "fullscreen";
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

  destroy(): void {
    if (this.destroyed) {
      return;
    }
    this.destroyed = true;
    window.removeEventListener("message", this.handleMessage);
    const error = new EmbedError(
      "EMBED_DESTROYED",
      "The embedded screen was destroyed.",
    );
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timeout);
      pending.reject(error);
    }
    this.pending.clear();
    this.errorListeners.clear();
    this.iframe.remove();
  }

  private post(message: HostMessage): void {
    if (this.destroyed) {
      throw new EmbedError(
        "EMBED_DESTROYED",
        "The embedded screen was destroyed.",
      );
    }
    this.iframe.contentWindow?.postMessage(message, this.origin);
  }

  private request<T>(
    expected: PendingRequest["expected"],
    message: Exclude<HostMessage, { type: "refresh" }>,
  ): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pending.delete(message.request_id);
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
      });
      try {
        this.post(message);
      } catch (error) {
        clearTimeout(timeout);
        this.pending.delete(message.request_id);
        reject(
          error instanceof EmbedError
            ? error
            : new EmbedError("EMBED_REQUEST_FAILED", String(error)),
        );
      }
    });
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
      this.isReady = true;
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
    if (message.request_id) {
      const pending = this.pending.get(message.request_id);
      if (pending) {
        clearTimeout(pending.timeout);
        this.pending.delete(message.request_id);
        pending.reject(error);
      }
    }
    for (const listener of this.errorListeners) {
      listener(error);
    }
  }

  private resolveRequest(message: AckMessage | ParametersMessage): void {
    const pending = this.pending.get(message.request_id);
    if (!pending || pending.expected !== message.type) {
      return;
    }
    clearTimeout(pending.timeout);
    this.pending.delete(message.request_id);
    pending.resolve(
      message.type === "parameters"
        ? structuredClone(message.parameters)
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
