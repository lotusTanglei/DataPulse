import { afterEach, expect, test, vi } from "vitest";
import { createSpeechPlayback } from "./speechPlayback";

const options = {
  text: "Current value 123", audioUrl: "blob:audio", language: "en-US", rate: 1,
  pitch: 1, volume: 0.8, maxSeconds: 30,
};

class FakeAudio {
  static instances: FakeAudio[] = [];
  currentTime = 0;
  duration = 12;
  volume = 1;
  playbackRate = 1;
  onplaying: (() => void) | null = null;
  onended: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onwaiting: (() => void) | null = null;
  ontimeupdate: (() => void) | null = null;
  play = vi.fn(async () => { this.onplaying?.(); });
  pause = vi.fn();
  removeAttribute = vi.fn();
  load = vi.fn();
  constructor() { FakeAudio.instances.push(this); }
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  FakeAudio.instances = [];
});

test("pauses and resumes the same audio position and releases media on abort", async () => {
  vi.stubGlobal("Audio", FakeAudio);
  const abort = new AbortController();
  const started = vi.fn();
  const playback = createSpeechPlayback(options, abort.signal, started);
  const audio = FakeAudio.instances[0]!;
  expect(started).toHaveBeenCalledOnce();
  audio.currentTime = 4;
  playback.pause();
  playback.resume();
  expect(audio.currentTime).toBe(4);
  playback.setVolume(0.3);
  expect(audio.volume).toBe(0.3);
  abort.abort();
  await playback.done;
  expect(audio.onplaying).toBeNull();
  expect(audio.removeAttribute).toHaveBeenCalledWith("src");
  expect(audio.load).toHaveBeenCalled();
});

test("reports autoplay refusal and does not leave the queue waiting", async () => {
  class BlockedAudio extends FakeAudio {
    play = vi.fn(async () => { throw new DOMException("Blocked", "NotAllowedError"); });
  }
  vi.stubGlobal("Audio", BlockedAudio);
  const playback = createSpeechPlayback(options, new AbortController().signal, vi.fn());
  await expect(playback.done).rejects.toMatchObject({ code: "SPEECH_GESTURE_REQUIRED" });
  expect(FakeAudio.instances[0]!.onended).toBeNull();
});

test("times out silent starts and cancels callbacks from a previous task", async () => {
  vi.useFakeTimers();
  class SilentAudio extends FakeAudio {
    play = vi.fn(async () => {});
  }
  vi.stubGlobal("Audio", SilentAudio);
  const started = vi.fn();
  const playback = createSpeechPlayback(options, new AbortController().signal, started);
  const rejected = expect(playback.done).rejects.toMatchObject({ code: "SPEECH_START_TIMEOUT" });
  const oldCallback = FakeAudio.instances[0]!.onplaying!;
  await vi.advanceTimersByTimeAsync(5000);
  await rejected;
  oldCallback();
  expect(started).not.toHaveBeenCalled();
});

test("enforces a maximum playback duration", async () => {
  vi.useFakeTimers();
  vi.stubGlobal("Audio", FakeAudio);
  const playback = createSpeechPlayback({ ...options, maxSeconds: 1 }, new AbortController().signal, vi.fn());
  const rejected = expect(playback.done).rejects.toMatchObject({ code: "SPEECH_DURATION_LIMIT" });
  await vi.advanceTimersByTimeAsync(1000);
  await rejected;
});

test("uses an existing video element and reports its clock, duration and actual active time", async () => {
  vi.useFakeTimers();
  const video = new FakeAudio();
  const timeline = vi.fn();
  const started = vi.fn();
  const playback = createSpeechPlayback({ ...options, mediaElement: video as unknown as HTMLVideoElement }, new AbortController().signal, started, timeline);
  await vi.advanceTimersByTimeAsync(1000);
  video.currentTime = 2;
  video.ontimeupdate!();
  expect(timeline).toHaveBeenLastCalledWith({ currentSeconds: 2, durationSeconds: 12, activeSeconds: 1, charIndex: null });
  playback.pause();
  await vi.advanceTimersByTimeAsync(60000);
  expect(playback.getActiveSeconds()).toBe(1);
  playback.resume();
  await vi.advanceTimersByTimeAsync(1000);
  expect(playback.getActiveSeconds()).toBe(2);
  expect(started).toHaveBeenCalledOnce();
  playback.stop();
  await playback.done;
  expect(video.ontimeupdate).toBeNull();
  expect(vi.getTimerCount()).toBe(0);
});

test("preserves the remaining duration budget across repeated pause and resume", async () => {
  vi.useFakeTimers();
  vi.stubGlobal("Audio", FakeAudio);
  const playback = createSpeechPlayback({ ...options, maxSeconds: 2 }, new AbortController().signal, vi.fn());
  const rejected = expect(playback.done).rejects.toMatchObject({ code: "SPEECH_DURATION_LIMIT" });
  await vi.advanceTimersByTimeAsync(750);
  playback.pause();
  await vi.advanceTimersByTimeAsync(20000);
  playback.resume();
  await vi.advanceTimersByTimeAsync(750);
  playback.pause();
  await vi.advanceTimersByTimeAsync(20000);
  playback.resume();
  await vi.advanceTimersByTimeAsync(500);
  await rejected;
  expect(playback.getActiveSeconds()).toBe(2);
});

test("buffering suspends the active budget and a stalled stream has a bounded wait", async () => {
  vi.useFakeTimers();
  vi.stubGlobal("Audio", FakeAudio);
  const playback = createSpeechPlayback({ ...options, maxSeconds: 2 }, new AbortController().signal, vi.fn());
  const rejected = expect(playback.done).rejects.toMatchObject({ code: "SPEECH_MEDIA_STALLED" });
  const audio = FakeAudio.instances[0]!;
  await vi.advanceTimersByTimeAsync(500);
  audio.onwaiting!();
  await vi.advanceTimersByTimeAsync(4000);
  audio.onwaiting!();
  await vi.advanceTimersByTimeAsync(1000);
  await rejected;
  expect(playback.getActiveSeconds()).toBe(0.5);
});

test("metadata updates report only finite durations and cancelled media cannot publish late events", async () => {
  vi.stubGlobal("Audio", FakeAudio);
  const timeline = vi.fn();
  const abort = new AbortController();
  const playback = createSpeechPlayback(options, abort.signal, vi.fn(), timeline);
  const audio = FakeAudio.instances[0]!;
  audio.duration = Infinity;
  audio.ontimeupdate!();
  expect(timeline.mock.lastCall![0].durationSeconds).toBeNull();
  const oldEvent = audio.ontimeupdate!;
  abort.abort();
  await playback.done;
  const count = timeline.mock.calls.length;
  oldEvent();
  playback.resume();
  playback.setVolume(0.2);
  expect(timeline).toHaveBeenCalledTimes(count);
  expect(audio.volume).toBe(options.volume);
});

test("speech boundary events select characters and cancellation while paused excludes idle time", async () => {
  vi.useFakeTimers();
  vi.stubGlobal("SpeechSynthesisUtterance", class {});
  let utterance: SpeechSynthesisUtterance;
  vi.stubGlobal("speechSynthesis", {
    speak(value: SpeechSynthesisUtterance) { utterance = value; value.onstart?.({} as SpeechSynthesisEvent); },
    pause: vi.fn(), resume: vi.fn(), cancel: vi.fn(),
  });
  const timeline = vi.fn();
  const playback = createSpeechPlayback({ ...options, audioUrl: "" }, new AbortController().signal, vi.fn(), timeline);
  await vi.advanceTimersByTimeAsync(500);
  utterance!.onboundary?.({ charIndex: 8 } as SpeechSynthesisEvent);
  expect(timeline.mock.lastCall![0]).toMatchObject({ charIndex: 8, currentSeconds: 0.5 });
  playback.pause();
  await vi.advanceTimersByTimeAsync(60000);
  playback.stop();
  await playback.done;
  expect(playback.getActiveSeconds()).toBe(0.5);
  expect(utterance!.onboundary).toBeNull();
  expect(vi.getTimerCount()).toBe(0);
});

test("downgrades unavailable speech languages before reporting a voice error", async () => {
  vi.useFakeTimers();
  vi.stubGlobal("SpeechSynthesisUtterance", class {});
  const utterances: SpeechSynthesisUtterance[] = [];
  const speech = {
    speak: vi.fn((value: SpeechSynthesisUtterance) => utterances.push(value)),
    pause: vi.fn(), resume: vi.fn(), cancel: vi.fn(),
  };
  vi.stubGlobal("speechSynthesis", speech);
  const playback = createSpeechPlayback(
    { ...options, audioUrl: "", language: "zh-Hant-TW", languageFallbacks: ["zh", "en-US"] },
    new AbortController().signal,
    vi.fn(),
  );
  expect(utterances[0]!.lang).toBe("zh-Hant-TW");
  utterances[0]!.onerror?.({ error: "language-unavailable" } as SpeechSynthesisErrorEvent);
  expect(speech.cancel).toHaveBeenCalledOnce();
  expect(utterances[1]!.lang).toBe("zh");
  utterances[1]!.onerror?.({ error: "voice-unavailable" } as SpeechSynthesisErrorEvent);
  expect(utterances[2]!.lang).toBe("en-US");
  utterances[2]!.onstart?.({} as SpeechSynthesisEvent);
  utterances[2]!.onend?.({} as SpeechSynthesisEvent);
  await playback.done;
});
