import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { DataPulseEmbed, type DigitalHumanCommand, type EmbeddedScreen } from "./index";
import { isPlayerMessage } from "./protocol";

const mounted = new Set<EmbeddedScreen>();

beforeEach(() => {
  const createElement = document.createElement.bind(document);
  vi.spyOn(document, "createElement").mockImplementation((name, options) => {
    const element = createElement(name, options);
    // Keep a real message window without navigating to an external test host.
    if (name === "iframe") (element as HTMLIFrameElement).srcdoc = "<!doctype html><title>Embed fixture</title>";
    return element;
  });
});

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
  const embedded = DataPulseEmbed.mount(container, {
    url: "https://data.example.com/embed/screen-1",
    ticket: "short-ticket",
  });
  vi.spyOn(embedded.iframe.contentWindow!, "postMessage").mockImplementation(() => {});
  mounted.add(embedded);
  return embedded;
}

afterEach(() => {
  for (const embedded of mounted) embedded.destroy();
  mounted.clear();
  document.body.replaceChildren();
  vi.useRealTimers();
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

  test("negotiates digital human controls and correlates state replies", async () => {
    const embedded = mountEmbed();
    await expect(embedded.digitalHuman({ component_id: "speaker", action: "getStatus" })).rejects.toMatchObject({ code: "EMBED_PLAYER_NOT_READY" });
    dispatchFrom(embedded, "https://data.example.com", {
      type: "ready", instance_id: embedded.instanceId, protocol_version: 1, capabilities: ["digitalHuman.v1"],
    });
    const postMessage = vi.spyOn(embedded.iframe.contentWindow!, "postMessage");
    const response = embedded.digitalHuman({ component_id: "speaker", action: "mute", enabled: true });
    const request = postMessage.mock.calls.at(-1)![0] as { request_id: string };
    const state = { component_id: "speaker", status: "muted", code: null, muted: true, volume: 0.5 };
    dispatchFrom(embedded, "https://data.example.com", {
      type: "digitalHumanStatus", instance_id: embedded.instanceId, request_id: request.request_id, state,
    });
    await expect(response).resolves.toEqual(state);
    const listener = vi.fn();
    embedded.onDigitalHuman(listener);
    const event = { component_id: "speaker", status: "speaking", task_id: "task-1", source: "host", code: null, request_id: "", timestamp: 1 };
    dispatchFrom(embedded, "https://evil.example.com", { type: "digitalHumanEvent", instance_id: embedded.instanceId, event });
    expect(listener).not.toHaveBeenCalled();
    dispatchFrom(embedded, "https://data.example.com", { type: "digitalHumanEvent", instance_id: embedded.instanceId, event });
    expect(listener).toHaveBeenCalledWith(event);
    embedded.destroy();
  });

  test("accepts complete subtitle cue events and rejects incomplete cues", () => {
    const valid = {
      type: "digitalHumanEvent",
      instance_id: "embed-1",
      event: {
        name: "subtitleCue",
        component_id: "speaker",
        status: "speaking",
        task_id: "task-1",
        source: "ranking_change",
        code: null,
        request_id: "request-1",
        timestamp: 1000,
        cue_index: 0,
        cue_text: "Hello",
        cue_start: 0,
        cue_end: 1.25,
      },
    };
    expect(isPlayerMessage(valid)).toBe(true);
    expect(isPlayerMessage({
      ...valid,
      event: { ...valid.event, cue_end: 0 },
    })).toBe(false);
    expect(isPlayerMessage({
      ...valid,
      event: { ...valid.event, cue_text: undefined },
    })).toBe(false);
  });

  test("old players reject unsupported speech controls immediately", async () => {
    const embedded = mountEmbed();
    dispatchFrom(embedded, "https://data.example.com", { type: "ready", instance_id: embedded.instanceId, protocol_version: 1 });
    await expect(embedded.digitalHuman({ component_id: "speaker", action: "play" })).rejects.toMatchObject({ code: "EMBED_CAPABILITY_UNAVAILABLE" });
    embedded.destroy();
  });

  test.each([
    null,
    { component_id: " ", action: "play" },
    { component_id: "speaker", action: "mute" },
    { component_id: "speaker", action: "mute", enabled: "true" },
    { component_id: "speaker", action: "setVolume", volume: NaN },
    { component_id: "speaker", action: "setVolume", volume: 2 },
    { component_id: "speaker", action: "play", volume: 1 },
    { component_id: "speaker", action: "speak", text: "Unpublished text" },
    { component_id: "speaker", action: "unknown" },
  ])("rejects invalid speech commands without sending them: %j", async (command) => {
    const embedded = mountEmbed();
    dispatchFrom(embedded, "https://data.example.com", {
      type: "ready", instance_id: embedded.instanceId, protocol_version: 1, capabilities: ["digitalHuman.v1"],
    });
    const post = vi.spyOn(embedded.iframe.contentWindow!, "postMessage");
    await expect(embedded.digitalHuman(command as DigitalHumanCommand)).rejects.toMatchObject({ code: "DIGITAL_HUMAN_COMMAND_INVALID" });
    expect(post).not.toHaveBeenCalled();
  });

  test("ignores speech replies for a different component and supports cancellation", async () => {
    const embedded = mountEmbed();
    dispatchFrom(embedded, "https://data.example.com", {
      type: "ready", instance_id: embedded.instanceId, protocol_version: 1, capabilities: ["digitalHuman.v1"],
    });
    const post = vi.spyOn(embedded.iframe.contentWindow!, "postMessage");
    const abort = new AbortController();
    const response = embedded.digitalHuman({ component_id: "speaker", action: "play" }, { signal: abort.signal });
    const resolved = vi.fn();
    void response.then(resolved, () => {});
    const request = post.mock.calls.at(-1)![0] as { request_id: string };
    dispatchFrom(embedded, "https://data.example.com", {
      type: "digitalHumanStatus", instance_id: embedded.instanceId, request_id: request.request_id,
      state: { component_id: "other", status: "speaking", code: null, muted: false, volume: 1 },
    });
    await Promise.resolve();
    expect(resolved).not.toHaveBeenCalled();
    abort.abort();
    await expect(response).rejects.toMatchObject({ code: "EMBED_REQUEST_CANCELLED" });
    await expect(embedded.digitalHuman({ component_id: "speaker", action: "play" }, { signal: abort.signal })).rejects.toMatchObject({ code: "EMBED_REQUEST_CANCELLED" });
    expect(post).toHaveBeenCalledOnce();
  });

  test("speech requests time out and reject immediately on destroy", async () => {
    vi.useFakeTimers();
    const embedded = mountEmbed();
    dispatchFrom(embedded, "https://data.example.com", {
      type: "ready", instance_id: embedded.instanceId, protocol_version: 1, capabilities: ["digitalHuman.v1"],
    });
    const timeout = expect(embedded.digitalHuman({ component_id: "speaker", action: "getStatus" })).rejects.toMatchObject({ code: "EMBED_REQUEST_TIMEOUT" });
    await vi.advanceTimersByTimeAsync(10_000);
    await timeout;
    const destroyed = expect(embedded.digitalHuman({ component_id: "speaker", action: "play" })).rejects.toMatchObject({ code: "EMBED_DESTROYED" });
    embedded.destroy();
    await destroyed;
    expect(embedded.ready).toBe(false);
    expect(vi.getTimerCount()).toBe(0);
  });

  test("ticket expiration rejects all outstanding requests and cannot be undone by late ready", async () => {
    const embedded = mountEmbed();
    const ready = { type: "ready", instance_id: embedded.instanceId, protocol_version: 1, capabilities: ["digitalHuman.v1"] };
    dispatchFrom(embedded, "https://data.example.com", ready);
    const speech = expect(embedded.digitalHuman({ component_id: "speaker", action: "play" })).rejects.toMatchObject({ code: "EMBED_TICKET_EXPIRED" });
    const parameters = expect(embedded.getParameters()).rejects.toMatchObject({ code: "EMBED_TICKET_EXPIRED" });
    dispatchFrom(embedded, "https://data.example.com", {
      type: "error", instance_id: embedded.instanceId, code: "EMBED_TICKET_EXPIRED", message: "Ticket expired.",
    });
    await speech;
    await parameters;
    dispatchFrom(embedded, "https://data.example.com", ready);
    expect(embedded.ready).toBe(false);
    await expect(embedded.digitalHuman({ component_id: "speaker", action: "play" })).rejects.toMatchObject({ code: "EMBED_TICKET_EXPIRED" });
    expect(() => embedded.refresh()).toThrow(expect.objectContaining({ code: "EMBED_TICKET_EXPIRED" }));
  });
});
