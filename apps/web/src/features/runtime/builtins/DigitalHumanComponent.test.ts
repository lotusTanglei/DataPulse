import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";
import type { DashboardDocument } from "../../../contracts";
import ScreenRuntime from "../ScreenRuntime.vue";
import DigitalHumanComponent from "./DigitalHumanComponent.vue";
import type { ComponentInstance } from "../types";
import { pageSpeechQueue } from "../speechQueue";
import type { SpeechEvent } from "../speechProtocol";

const speaker: ComponentInstance = {
  id: "speaker", type: "builtin.digital_human",
  frame: { x: 320, y: 0, width: 320, height: 420 },
  props: { name: "播报员", speech_template: "本月销售 {{sales.value | number}}", muted: true },
  data_binding: { source: "components", variables: [{ name: "sales.value", component_id: "kpi", field: "amount" }] },
};
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); vi.useRealTimers(); });

test("references existing QueryResult without an extra query in the unified player", async () => {
  const queryComponent = vi.fn(async (_componentId: string) => ({
    request_id: "query-1", columns: [{ name: "amount", data_type: "number" }],
    rows: [[1234]], row_count: 1, duration_ms: 1, truncated: false,
  }));
  const document: DashboardDocument = {
    canvas: { width: 1920, height: 1080 },
    components: [
      { id: "kpi", type: "builtin.kpi", frame: { x: 0, y: 0, width: 280, height: 160 }, data_binding: { chart_spec: { dataset_id: "sales" } } },
      speaker,
    ],
  };
  const wrapper = mount(ScreenRuntime, { props: {
    document, loadAsset: vi.fn(), queryComponent, mode: "standalone",
  } });
  await flushPromises();
  expect(wrapper.find(".digital-human__subtitle").text()).toBe("本月销售 1,234");
  expect(queryComponent).toHaveBeenCalledOnce();
  expect(queryComponent.mock.calls[0]?.[0]).toBe("kpi");
  expect(wrapper.find(".digital-human").attributes("data-status")).toBe("muted");
  await wrapper.vm.refresh();
  await flushPromises();
  expect(queryComponent).toHaveBeenCalledTimes(2);
  wrapper.unmount();
  expect(pageSpeechQueue.size()).toBe(0);
});

test("no voice engine falls back visibly and remains controllable", async () => {
  vi.stubGlobal("speechSynthesis", undefined);
  const wrapper = mount(DigitalHumanComponent, { props: {
    instance: { ...speaker, props: { speech_template: "欢迎", muted: false, auto_play: false }, data_binding: {} },
    result: null, loading: false, error: null, loadAsset: vi.fn(), mode: "preview",
  } });
  await flushPromises();
  await wrapper.get('[aria-label="播放播报"]').trigger("click");
  await flushPromises();
  expect(wrapper.attributes("data-status")).toBe("fallback");
  expect(wrapper.text()).toContain("SPEECH_VOICE_UNAVAILABLE");
  await wrapper.get('[aria-label="停止播报"]').trigger("click");
  expect(wrapper.attributes("data-status")).toBe("idle");
  wrapper.unmount();
});

test("focusable digital human region exposes keyboard playback controls", async () => {
  vi.stubGlobal("SpeechSynthesisUtterance", class {});
  vi.stubGlobal("speechSynthesis", {
    speak: (utterance: SpeechSynthesisUtterance) => utterance.onstart?.({} as SpeechSynthesisEvent),
    cancel: vi.fn(), pause: vi.fn(), resume: vi.fn(),
  });
  const wrapper = mount(DigitalHumanComponent, { props: {
    instance: { ...speaker, props: { speech_template: "欢迎", muted: false, auto_play: false }, data_binding: {} },
    result: null, loading: false, error: null, loadAsset: vi.fn(), mode: "preview",
  } });
  try {
    const region = wrapper.get(".digital-human");
    expect(region.attributes("tabindex")).toBe("0");
    expect(region.attributes("aria-keyshortcuts")).toContain("Space");
    expect(region.attributes("aria-describedby")).toContain("subtitle");
    await region.trigger("keydown", { key: " " });
    await flushPromises();
    expect(region.attributes("data-status")).toBe("speaking");
    await region.trigger("keydown", { key: "m" });
    expect(region.attributes("data-muted")).toBe("true");
    await region.trigger("keydown", { key: "c" });
    expect(wrapper.find(".digital-human__subtitle").exists()).toBe(false);
    await region.trigger("keydown", { key: "Escape" });
    expect(region.attributes("data-status")).toBe("idle");
  } finally {
    wrapper.unmount();
  }
});

test("validated action assets are shown only when their condition matches speech", async () => {
  vi.stubGlobal("SpeechSynthesisUtterance", class {});
  vi.stubGlobal("speechSynthesis", {
    speak: (utterance: SpeechSynthesisUtterance) => utterance.onstart?.({} as SpeechSynthesisEvent),
    cancel: vi.fn(), pause: vi.fn(), resume: vi.fn(),
  });
  const wrapper = mount(DigitalHumanComponent, { props: {
    instance: { ...speaker, props: {
      speech_template: "欢迎", muted: false, auto_play: false,
      actions: [{ id: "wave", kind: "wave", asset_id: "wave", asset_kind: "image", duration_ms: 1200,
        conditions: [{ variable: "value", operator: "gt", value: 10 }], condition_mode: "all" }],
    }, data_binding: {} },
    result: { request_id: "r", columns: [{ name: "amount", data_type: "number" }], rows: [[12]], row_count: 1, duration_ms: 1, truncated: false },
    loading: false, error: null, loadAsset: async (id: string) => `blob:${id}`,
  } });
  try {
    await flushPromises();
    await wrapper.get('[aria-label="播放播报"]').trigger("click");
    await flushPromises();
    expect(wrapper.find(".digital-human__action img").attributes("src")).toBe("blob:wave");
  } finally {
    wrapper.unmount();
  }
});

test("matching actions use priority before stable action id", async () => {
  vi.stubGlobal("SpeechSynthesisUtterance", class {});
  vi.stubGlobal("speechSynthesis", {
    speak: (utterance: SpeechSynthesisUtterance) => utterance.onstart?.({} as SpeechSynthesisEvent),
    cancel: vi.fn(), pause: vi.fn(), resume: vi.fn(),
  });
  const wrapper = mount(DigitalHumanComponent, { props: {
    instance: { ...speaker, props: {
      speech_template: "欢迎", muted: false, auto_play: false,
      actions: [
        { id: "z-low", kind: "wave", asset_id: "low", asset_kind: "image", priority: 1, duration_ms: 1200 },
        { id: "a-high", kind: "nod", asset_id: "high", asset_kind: "image", priority: 5, duration_ms: 1200 },
      ],
    }, data_binding: {} },
    result: null, loading: false, error: null, loadAsset: async (id: string) => `blob:${id}`,
  } });
  try {
    await flushPromises();
    await wrapper.get('[aria-label="播放播报"]').trigger("click");
    await flushPromises();
    expect(wrapper.find(".digital-human__action img").attributes("src")).toBe("blob:high");
  } finally { wrapper.unmount(); }
});

test("action asset blob URLs are released when the component is unmounted", async () => {
  const revoke = vi.fn();
  vi.stubGlobal("URL", { revokeObjectURL: revoke });
  vi.stubGlobal("SpeechSynthesisUtterance", class {});
  vi.stubGlobal("speechSynthesis", {
    speak: (utterance: SpeechSynthesisUtterance) => utterance.onstart?.({} as SpeechSynthesisEvent),
    cancel: vi.fn(), pause: vi.fn(), resume: vi.fn(),
  });
  const wrapper = mount(DigitalHumanComponent, { props: {
    instance: { ...speaker, props: {
      speech_template: "欢迎", muted: false, auto_play: false,
      actions: [{ id: "wave", kind: "wave", asset_id: "wave", asset_kind: "image", duration_ms: 1200 }],
    }, data_binding: {} },
    result: null, loading: false, error: null,
    loadAsset: async (id: string) => `blob:${id}`,
  } });
  await flushPromises();
  await wrapper.get('[aria-label="播放播报"]').trigger("click");
  await flushPromises();
  wrapper.unmount();
  expect(revoke).toHaveBeenCalledWith("blob:wave");
});

test("late asset loads are revoked after the component is unmounted", async () => {
  const revoke = vi.fn();
  vi.stubGlobal("URL", { revokeObjectURL: revoke });
  let resolveAsset: (value: string) => void = () => {};
  const wrapper = mount(DigitalHumanComponent, { props: {
    instance: { ...speaker, props: { speech_template: "欢迎", avatar_asset_id: "avatar" }, data_binding: {} },
    result: null, loading: false, error: null,
    loadAsset: () => new Promise<string>((resolve) => { resolveAsset = resolve; }),
  } });
  wrapper.unmount();
  resolveAsset("blob:late-image");
  await flushPromises();
  expect(revoke).toHaveBeenCalledWith("blob:late-image");
});

test("the editor does not autoplay even when the published configuration enables sound", async () => {
  const speak = vi.fn();
  vi.stubGlobal("speechSynthesis", { speak });
  const wrapper = mount(DigitalHumanComponent, { props: {
    instance: { ...speaker, props: { speech_template: "欢迎", muted: false }, data_binding: {} },
    result: null, loading: false, error: null, loadAsset: vi.fn(), mode: "editor",
  } });
  await flushPromises();
  expect(speak).not.toHaveBeenCalled();
  expect(wrapper.attributes("data-status")).toBe("ready");
  wrapper.unmount();
});

test.each(["completed", "stopped", "failed"])("speech lifecycle has one start and one terminal event when %s", async (outcome) => {
  let utterance: SpeechSynthesisUtterance | null = null;
  vi.stubGlobal("SpeechSynthesisUtterance", class {});
  vi.stubGlobal("speechSynthesis", {
    speak: (value: SpeechSynthesisUtterance) => {
      utterance = value;
      value.onstart?.(new Event("start") as SpeechSynthesisEvent);
    },
    cancel: vi.fn(), pause: vi.fn(), resume: vi.fn(),
  });
  const wrapper = mount(DigitalHumanComponent, { props: {
    instance: { ...speaker, props: { speech_template: "欢迎", muted: false, auto_play: false }, data_binding: {} },
    result: null, loading: false, error: null, loadAsset: vi.fn(), mode: "preview",
  } });
  try {
    await flushPromises();
    await wrapper.get('[aria-label="播放播报"]').trigger("click");
    await flushPromises();
    const active = utterance as unknown as SpeechSynthesisUtterance;
    const lateEnd = active.onend!;
    await wrapper.get('[aria-label="暂停播报"]').trigger("click");
    await wrapper.get('[aria-label="播放播报"]').trigger("click");
    if (outcome === "completed") active.onend?.(new Event("end") as SpeechSynthesisEvent);
    else if (outcome === "stopped") await wrapper.get('[aria-label="停止播报"]').trigger("click");
    else active.onerror?.({ error: "synthesis-failed" } as SpeechSynthesisErrorEvent);
    await flushPromises();
    lateEnd.call(active, new Event("end") as SpeechSynthesisEvent);
    await flushPromises();
    const events = wrapper.emitted("speechEvent")!.map(([event]) => event as SpeechEvent);
    expect(events.filter((event) => event.name === "digitalHumanReady")).toHaveLength(1);
    const starts = events.filter((event) => event.name === "speechStart");
    expect(starts).toHaveLength(1);
    const terminal = events.filter((event) => ["speechEnd", "speechError"].includes(event.name));
    expect(terminal).toHaveLength(1);
    expect(terminal[0]!.task_id).toBe(starts[0]!.task_id);
    expect(terminal[0]!.source).toBe("manual");
    if (outcome !== "failed") expect(terminal[0]!.outcome).toBe(outcome);
    else expect(events.some((event) => event.name === "fallback")).toBe(true);
  } finally {
    wrapper.unmount();
  }
});

test("video original audio keeps its DOM node, real subtitle clock and position across mute and pause", async () => {
  vi.useFakeTimers();
  const playMedia = vi.spyOn(HTMLMediaElement.prototype, "play").mockImplementation(function (this: HTMLMediaElement) {
    this.dispatchEvent(new Event("playing"));
    return Promise.resolve();
  });
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
  vi.spyOn(HTMLMediaElement.prototype, "load").mockImplementation(() => {});
  const wrapper = mount(DigitalHumanComponent, { props: {
    instance: { ...speaker, data_binding: {}, props: {
      speech_template: "第一句。第二句。", muted: false, auto_play: false, speech_source: "video",
      speaking_asset_id: "movie", speaking_kind: "video", max_duration_seconds: 2,
      recording: { asset_id: "movie", sha256: "a".repeat(64), transcript: "第一句。第二句。", duration_seconds: 4,
        cues: [{ start: 0, end: 1, text: "第一句。" }, { start: 2, end: 4, text: "第二句。" }] },
    } },
    result: null, loading: false, error: null, loadAsset: async () => "blob:movie",
  } });
  try {
    await flushPromises();
    await wrapper.get('[aria-label="播放播报"]').trigger("click");
    await flushPromises();
    const video = wrapper.get(".digital-human__speech-video").element as HTMLVideoElement;
    Object.defineProperty(video, "duration", { configurable: true, value: 4 });
    expect(video.loop).toBe(false);
    expect(video.muted).toBe(false);
    expect(wrapper.get(".is-current").text()).toBe("第一句。");
    video.currentTime = 1.5;
    video.dispatchEvent(new Event("timeupdate"));
    await flushPromises();
    expect(wrapper.find(".is-current").exists()).toBe(false);
    video.currentTime = 2;
    video.dispatchEvent(new Event("timeupdate"));
    await flushPromises();
    expect(wrapper.get(".is-current").text()).toBe("第二句。");
    expect(wrapper.get('[role="progressbar"]').attributes("aria-valuenow")).toBe("50");
    await wrapper.get('[aria-label="静音"]').trigger("click");
    expect(video.volume).toBe(0);
    expect(wrapper.attributes("data-status")).toBe("speaking");
    await wrapper.get('[aria-label="暂停播报"]').trigger("click");
    await vi.advanceTimersByTimeAsync(30000);
    expect(wrapper.attributes("data-status")).toBe("paused");
    expect(wrapper.get('[role="progressbar"]').attributes("aria-valuenow")).toBe("50");
    await wrapper.get('[aria-label="启用声音"]').trigger("click");
    expect(wrapper.attributes("data-status")).toBe("paused");
    expect(video.volume).toBe(1);
    await wrapper.get('[aria-label="播放播报"]').trigger("click");
    expect(wrapper.get(".digital-human__speech-video").element).toBe(video);
    expect(video.currentTime).toBe(2);
    expect(playMedia).toHaveBeenCalledTimes(2);
    video.dispatchEvent(new Event("ended"));
    await flushPromises();
    expect(wrapper.attributes("data-status")).toBe("idle");
    expect(video.getAttribute("src")).toBeNull();
  } finally { wrapper.unmount(); }
});

test("stale prerecorded values never play and do not supply the current subtitles", async () => {
  const audio = vi.fn();
  vi.stubGlobal("Audio", audio);
  vi.stubGlobal("SpeechSynthesisUtterance", class {});
  const speak = vi.fn((utterance: SpeechSynthesisUtterance) => utterance.onstart?.({} as SpeechSynthesisEvent));
  vi.stubGlobal("speechSynthesis", { speak, cancel: vi.fn(), pause: vi.fn(), resume: vi.fn() });
  const wrapper = mount(DigitalHumanComponent, { props: {
    instance: { ...speaker, data_binding: {}, props: {
      speech_template: "当前 456", muted: false, auto_play: false, audio_asset_id: "voice",
      recording: { asset_id: "voice", sha256: "a".repeat(64), transcript: "当前 123", duration_seconds: 2,
        cues: [{ start: 0, end: 2, text: "当前 123" }] },
    } },
    result: null, loading: false, error: null, loadAsset: async () => "blob:voice",
  } });
  try {
    await flushPromises();
    await wrapper.get('[aria-label="播放播报"]').trigger("click");
    await flushPromises();
    expect(audio).not.toHaveBeenCalled();
    expect(speak).toHaveBeenCalledOnce();
    expect(wrapper.get(".digital-human__subtitle").text()).toBe("当前 456");
    expect(wrapper.text()).toContain("SPEECH_RECORDING_MISMATCH");
    await wrapper.get('[aria-label="静音"]').trigger("click");
    expect(globalThis.speechSynthesis.pause).toHaveBeenCalledOnce();
    expect(globalThis.speechSynthesis.cancel).not.toHaveBeenCalled();
    await wrapper.get('[aria-label="启用声音"]').trigger("click");
    expect(globalThis.speechSynthesis.resume).toHaveBeenCalledOnce();
    expect(speak).toHaveBeenCalledOnce();
  } finally { wrapper.unmount(); }
});

test("media playback failure falls back to browser speech without changing the task", async () => {
  const media = {
    play: vi.fn(() => Promise.reject(new Error("decode failure"))),
    pause: vi.fn(),
    load: vi.fn(),
    removeAttribute: vi.fn(),
  } as unknown as HTMLAudioElement;
  const speak = vi.fn((value: SpeechSynthesisUtterance) => value.onstart?.({} as SpeechSynthesisEvent));
  vi.stubGlobal("Audio", vi.fn(() => media));
  vi.stubGlobal("SpeechSynthesisUtterance", class {});
  vi.stubGlobal("speechSynthesis", { speak, cancel: vi.fn(), pause: vi.fn(), resume: vi.fn() });
  const wrapper = mount(DigitalHumanComponent, { props: {
    instance: { ...speaker, data_binding: {}, props: {
      speech_template: "预录失败后回退", muted: false, auto_play: false,
      speech_source: "audio", audio_asset_id: "voice",
      recording: { asset_id: "voice", sha256: "a".repeat(64), transcript: "预录失败后回退", duration_seconds: 2 },
    } },
    result: null, loading: false, error: null, loadAsset: async () => "blob:voice",
  } });
  try {
    await flushPromises();
    await wrapper.get('[aria-label="播放播报"]').trigger("click");
    await flushPromises();
    expect(speak).toHaveBeenCalledOnce();
    expect(wrapper.attributes("data-status")).toBe("speaking");
    expect(wrapper.text()).toContain("SPEECH_MEDIA_FAILED");
    const events = (wrapper.emitted("speechEvent") ?? []).map(([event]) => event as SpeechEvent);
    expect(events.filter((event) => event.name === "speechStart")).toHaveLength(1);
    expect(events.find((event) => event.name === "speechStart")?.task_id).toBeTruthy();
  } finally { wrapper.unmount(); }
});

test("hidden subtitles retain an accessible live transcript and clamp unsafe visual settings", async () => {
  const wrapper = mount(DigitalHumanComponent, { props: {
    instance: { ...speaker, data_binding: {}, props: {
      speech_template: "无障碍播报", subtitle_enabled: false, subtitle_font_size: 1, subtitle_max_lines: 999,
      auto_play: false,
    } },
    result: null, loading: false, error: null, loadAsset: vi.fn(), mode: "preview",
  } });
  await flushPromises();
  expect(wrapper.find(".digital-human__subtitle").exists()).toBe(false);
  expect(wrapper.get(".digital-human__sr-subtitle").text()).toBe("无障碍播报");
  await wrapper.setProps({ instance: { ...speaker, data_binding: {}, props: {
    speech_template: "可见字幕", subtitle_enabled: true, subtitle_font_size: 1, subtitle_max_lines: 999, auto_play: false,
  } } });
  await flushPromises();
  const subtitle = wrapper.get(".digital-human__subtitle");
  expect(subtitle.attributes("style")).toContain("font-size: 12px");
  expect(subtitle.attributes("aria-atomic")).toBe("true");
  expect(subtitle.attributes("tabindex")).toBe("0");
  expect(subtitle.attributes("role")).toBe("log");
  expect(wrapper.get('[role="region"]').attributes("aria-labelledby")).toContain("digital-human-speaker-name");
  wrapper.unmount();
});

test("parameter changes cancel the previous speech generation before triggering again", async () => {
  let utterance: SpeechSynthesisUtterance | null = null;
  vi.stubGlobal("SpeechSynthesisUtterance", class {});
  vi.stubGlobal("speechSynthesis", {
    speak: (value: SpeechSynthesisUtterance) => {
      utterance = value;
      value.onstart?.(new Event("start") as SpeechSynthesisEvent);
    },
    cancel: vi.fn(), pause: vi.fn(), resume: vi.fn(),
  });
  const wrapper = mount(DigitalHumanComponent, { props: {
    instance: { ...speaker, data_binding: {}, props: {
      speech_template: "区域播报", muted: false, auto_play: true,
      trigger: { kind: "parameter", parameter: "region", include_host: true },
    } },
    result: null, loading: false, error: null, loadAsset: vi.fn(), mode: "standalone",
    parameters: { region: "east" }, parameterSource: "runtime",
  } });
  await flushPromises();
  await wrapper.get('[aria-label="播放播报"]').trigger("click");
  await flushPromises();
  await wrapper.setProps({ parameters: { region: "west" } });
  await flushPromises();
  expect(globalThis.speechSynthesis.cancel).toHaveBeenCalled();
  expect(wrapper.attributes("data-status")).toBe("speaking");
  expect(utterance).not.toBeNull();
  wrapper.unmount();
});

test.each([
  ["ranking_change", 1, 2],
  ["status_change", "normal", "warning"],
] as const)("%s triggers only when its selected value changes", async (kind, before, after) => {
  const speak = vi.fn((utterance: SpeechSynthesisUtterance) => utterance.onstart?.({} as SpeechSynthesisEvent));
  vi.stubGlobal("SpeechSynthesisUtterance", class {});
  vi.stubGlobal("speechSynthesis", { speak, cancel: vi.fn(), pause: vi.fn(), resume: vi.fn() });
  const wrapper = mount(DigitalHumanComponent, { props: {
    instance: { ...speaker, data_binding: {}, props: {
      speech_template: "变化播报", muted: false, auto_play: true,
      trigger: { kind, variable: "value", cooldown_seconds: 1 },
    } },
    result: { request_id: "before", columns: [{ name: "value", data_type: typeof before === "number" ? "number" : "string" }], rows: [[before]], row_count: 1, duration_ms: 1, truncated: false },
    loading: false, error: null, loadAsset: vi.fn(), mode: "standalone",
  } });
  try {
    await flushPromises();
    expect(speak).not.toHaveBeenCalled();
    await wrapper.setProps({ result: { request_id: "after", columns: [{ name: "value", data_type: typeof after === "number" ? "number" : "string" }], rows: [[after]], row_count: 1, duration_ms: 1, truncated: false } });
    await flushPromises();
    expect(speak).toHaveBeenCalledOnce();
    const starts = (wrapper.emitted("speechEvent") ?? []).map(([event]) => event as SpeechEvent).filter((event) => event.name === "speechStart");
    expect(starts).toHaveLength(1);
    expect(starts[0]!.source).toBe(kind);
  } finally {
    wrapper.unmount();
  }
});
