import { afterEach, describe, expect, test, vi } from "vitest";

import { DataPulseEmbed, type EmbeddedScreen } from "./index";

function dispatchFrom(
  embedded: EmbeddedScreen,
  origin: string,
  data: unknown,
): void {
  window.dispatchEvent(
    new MessageEvent("message", {
      data,
      origin,
      source: embedded.iframe.contentWindow,
    }),
  );
}

function mountEmbed(): EmbeddedScreen {
  const container = document.createElement("div");
  document.body.append(container);
  return DataPulseEmbed.mount(container, {
    url: "https://data.example.com/embed/screen-1",
    ticket: "short-ticket",
  });
}

afterEach(() => {
  document.body.replaceChildren();
  vi.restoreAllMocks();
});

describe("DataPulseEmbed", () => {
  test("builds a bootstrap-only ticket URL and uses an explicit target Origin", () => {
    const embedded = mountEmbed();
    const url = new URL(embedded.iframe.src);
    expect(url.origin).toBe("https://data.example.com");
    expect(url.pathname).toBe("/embed/screen-1");
    expect(url.searchParams.get("ticket")).toBe("short-ticket");
    expect(url.searchParams.get("instance_id")).toBe(embedded.instanceId);
    expect(embedded.iframe.referrerPolicy).toBe("no-referrer");

    const postMessage = vi.spyOn(
      embedded.iframe.contentWindow!,
      "postMessage",
    );
    embedded.refresh();
    expect(postMessage).toHaveBeenCalledWith(
      {
        type: "refresh",
        instance_id: embedded.instanceId,
      },
      "https://data.example.com",
    );
  });

  test("ignores messages from the wrong Origin or window", () => {
    const embedded = mountEmbed();
    dispatchFrom(embedded, "https://evil.example.com", {
      type: "ready",
      protocol_version: 1,
      instance_id: embedded.instanceId,
    });
    expect(embedded.ready).toBe(false);

    window.dispatchEvent(
      new MessageEvent("message", {
        data: {
          type: "ready",
          protocol_version: 1,
          instance_id: embedded.instanceId,
        },
        origin: "https://data.example.com",
        source: window,
      }),
    );
    expect(embedded.ready).toBe(false);

    dispatchFrom(embedded, "https://data.example.com", {
      type: "ready",
      protocol_version: 1,
      instance_id: embedded.instanceId,
    });
    expect(embedded.ready).toBe(true);
  });

  test("correlates parameter and fullscreen requests", async () => {
    const embedded = mountEmbed();
    const postMessage = vi.spyOn(
      embedded.iframe.contentWindow!,
      "postMessage",
    );

    const setPromise = embedded.setParameters({ region: "west" });
    const setMessage = postMessage.mock.calls.at(-1)?.[0] as {
      request_id: string;
    };
    dispatchFrom(embedded, "https://data.example.com", {
      type: "ack",
      instance_id: embedded.instanceId,
      request_id: setMessage.request_id,
    });
    await expect(setPromise).resolves.toBeUndefined();

    const getPromise = embedded.getParameters();
    const getMessage = postMessage.mock.calls.at(-1)?.[0] as {
      request_id: string;
    };
    dispatchFrom(embedded, "https://data.example.com", {
      type: "parameters",
      instance_id: embedded.instanceId,
      request_id: getMessage.request_id,
      parameters: { region: "east", year: 2026 },
    });
    await expect(getPromise).resolves.toEqual({
      region: "east",
      year: 2026,
    });

    const fullscreenPromise = embedded.fullscreen(false);
    const fullscreenMessage = postMessage.mock.calls.at(-1)?.[0] as {
      enabled: boolean;
      request_id: string;
    };
    expect(fullscreenMessage.enabled).toBe(false);
    dispatchFrom(embedded, "https://data.example.com", {
      type: "ack",
      instance_id: embedded.instanceId,
      request_id: fullscreenMessage.request_id,
    });
    await expect(fullscreenPromise).resolves.toBeUndefined();
  });

  test("rejects correlated errors and reports asynchronous player errors", async () => {
    const embedded = mountEmbed();
    const listener = vi.fn();
    embedded.onError(listener);
    const postMessage = vi.spyOn(
      embedded.iframe.contentWindow!,
      "postMessage",
    );

    const request = embedded.setParameters({ year: 2027 });
    const message = postMessage.mock.calls.at(-1)?.[0] as {
      request_id: string;
    };
    dispatchFrom(embedded, "https://data.example.com", {
      type: "error",
      instance_id: embedded.instanceId,
      request_id: message.request_id,
      code: "EMBED_PARAMETER_DENIED",
      message: "Parameter is immutable.",
    });
    await expect(request).rejects.toMatchObject({
      code: "EMBED_PARAMETER_DENIED",
    });

    dispatchFrom(embedded, "https://data.example.com", {
      type: "error",
      instance_id: embedded.instanceId,
      code: "EMBED_TICKET_EXPIRED",
      message: "Ticket expired.",
    });
    expect(listener).toHaveBeenCalledWith(
      expect.objectContaining({ code: "EMBED_TICKET_EXPIRED" }),
    );
  });

  test("supports independent embeds and removes listeners on destroy", () => {
    const first = mountEmbed();
    const second = mountEmbed();
    const firstError = vi.fn();
    const secondError = vi.fn();
    first.onError(firstError);
    second.onError(secondError);

    dispatchFrom(first, "https://data.example.com", {
      type: "error",
      instance_id: first.instanceId,
      code: "FIRST",
      message: "First only.",
    });
    expect(firstError).toHaveBeenCalledOnce();
    expect(secondError).not.toHaveBeenCalled();

    first.destroy();
    expect(first.iframe.isConnected).toBe(false);
    dispatchFrom(first, "https://data.example.com", {
      type: "error",
      instance_id: first.instanceId,
      code: "AFTER_DESTROY",
      message: "Ignored.",
    });
    expect(firstError).toHaveBeenCalledOnce();

    dispatchFrom(second, "https://data.example.com", {
      type: "ready",
      protocol_version: 1,
      instance_id: second.instanceId,
    });
    expect(second.ready).toBe(true);
  });
});
