export interface SpeechPlaybackOptions {
  text: string;
  audioUrl: string;
  language: string;
  rate: number;
  pitch: number;
  volume: number;
  maxSeconds: number;
  mediaElement?: HTMLMediaElement;
  languageFallbacks?: readonly string[];
}

export interface SpeechTimeline {
  currentSeconds: number;
  durationSeconds: number | null;
  activeSeconds: number;
  charIndex: number | null;
}

export class SpeechPlaybackError extends Error {
  constructor(readonly code: string) {
    super(code);
  }
}

export function createSpeechPlayback(
  options: SpeechPlaybackOptions,
  signal: AbortSignal,
  onStart: () => void,
  onTimeline: (timeline: SpeechTimeline) => void = () => {},
) {
  let media: HTMLMediaElement | null = null;
  let utterance: SpeechSynthesisUtterance | null = null;
  let languageCandidates: string[] = [];
  let languageIndex = 0;
  let finished = false;
  let started = false;
  let paused = false;
  let runningAt: number | null = null;
  let activeMs = 0;
  let charIndex: number | null = null;
  let rejectResult: (error: Error) => void = () => {};
  let resolveResult: () => void = () => {};
  let startTimeout: ReturnType<typeof setTimeout> | null = null;
  let durationTimeout: ReturnType<typeof setTimeout> | null = null;
  let ticker: ReturnType<typeof setInterval> | null = null;
  const done = new Promise<void>((resolve, reject) => {
    resolveResult = resolve;
    rejectResult = reject;
  });

  function activeSeconds(): number {
    return (activeMs + (runningAt === null ? 0 : Math.max(0, performance.now() - runningAt))) / 1000;
  }

  function report(): void {
    onTimeline({
      currentSeconds: media ? Math.max(0, media.currentTime || 0) : activeSeconds(),
      durationSeconds: media && Number.isFinite(media.duration) && media.duration > 0 ? media.duration : null,
      activeSeconds: activeSeconds(), charIndex,
    });
  }

  function suspendClock(): void {
    if (runningAt !== null) activeMs += Math.max(0, performance.now() - runningAt);
    runningAt = null;
    if (durationTimeout !== null) clearTimeout(durationTimeout);
    if (ticker !== null) clearInterval(ticker);
    durationTimeout = null;
    ticker = null;
  }

  function waitForPlayback(): void {
    if (startTimeout !== null) return;
    startTimeout = setTimeout(
      () => finish(new SpeechPlaybackError(started ? "SPEECH_MEDIA_STALLED" : "SPEECH_START_TIMEOUT")),
      5000,
    );
  }

  function finish(error?: Error): void {
    if (finished) return;
    finished = true;
    if (startTimeout !== null) clearTimeout(startTimeout);
    startTimeout = null;
    suspendClock();
    report();
    signal.removeEventListener("abort", cancel);
    if (media) {
      media.onplaying = null;
      media.onended = null;
      media.onerror = null;
      media.onwaiting = null;
      media.onpause = null;
      media.ontimeupdate = null;
      media.ondurationchange = null;
      media.onloadedmetadata = null;
      media.pause();
      media.removeAttribute("src");
      media.load();
    }
    if (utterance) {
      utterance.onstart = null;
      utterance.onend = null;
      utterance.onerror = null;
      utterance.onboundary = null;
      utterance.onpause = null;
      utterance.onresume = null;
      globalThis.speechSynthesis?.cancel();
    }
    if (error) rejectResult(error);
    else resolveResult();
  }

  function cancel(): void {
    finish();
  }

  function playing(): void {
    if (finished || signal.aborted) return;
    if (paused) { media?.pause(); return; }
    if (startTimeout !== null) clearTimeout(startTimeout);
    startTimeout = null;
    if (runningAt !== null) return;
    runningAt = performance.now();
    durationTimeout = setTimeout(
      () => finish(new SpeechPlaybackError("SPEECH_DURATION_LIMIT")),
      Math.max(0, options.maxSeconds * 1000 - activeMs),
    );
    ticker = setInterval(report, 100);
    if (!started) { started = true; onStart(); }
    report();
  }

  function buffering(): void {
    if (finished || paused) return;
    suspendClock();
    report();
    waitForPlayback();
  }

  function mediaProgress(): void {
    if (!finished && !paused) report();
  }

  function handleError(reason: unknown): void {
    const blocked = reason instanceof Error && reason.name === "NotAllowedError";
    finish(new SpeechPlaybackError(blocked ? "SPEECH_GESTURE_REQUIRED" : "SPEECH_MEDIA_FAILED"));
  }

  function startUtterance(): void {
    if (finished || signal.aborted) return;
    const language = languageCandidates[languageIndex] ?? "";
    utterance = new SpeechSynthesisUtterance(options.text);
    utterance.lang = language;
    utterance.rate = options.rate;
    utterance.pitch = options.pitch;
    utterance.volume = options.volume;
    utterance.onstart = playing;
    utterance.onend = () => finish();
    utterance.onboundary = (event) => {
      if (finished || paused || !Number.isFinite(event.charIndex)) return;
      charIndex = Math.max(0, Math.min(options.text.length, event.charIndex));
      report();
    };
    utterance.onpause = buffering;
    utterance.onresume = playing;
    utterance.onerror = (event) => {
      if (event.error === "not-allowed") {
        finish(new SpeechPlaybackError("SPEECH_GESTURE_REQUIRED"));
        return;
      }
      const canDowngrade =
        (event.error === "voice-unavailable" || event.error === "language-unavailable")
        && languageIndex + 1 < languageCandidates.length;
      if (canDowngrade) {
        languageIndex += 1;
        globalThis.speechSynthesis?.cancel();
        startUtterance();
        return;
      }
      finish(new SpeechPlaybackError("SPEECH_VOICE_UNAVAILABLE"));
    };
    try {
      globalThis.speechSynthesis.speak(utterance);
    } catch (error) {
      handleError(error);
    }
  }

  signal.addEventListener("abort", cancel, { once: true });
  if (signal.aborted) cancel();
  else {
    waitForPlayback();
    if (options.audioUrl) {
      try {
        media = options.mediaElement ?? new Audio();
        media.src = options.audioUrl;
        media.loop = false;
        media.autoplay = false;
        media.muted = false;
        media.volume = options.volume;
        media.playbackRate = options.rate;
        media.onplaying = playing;
        media.onended = () => finish();
        media.onerror = () => handleError(null);
        media.onwaiting = buffering;
        media.onpause = () => { if (media?.paused) buffering(); };
        media.ontimeupdate = mediaProgress;
        media.ondurationchange = mediaProgress;
        media.onloadedmetadata = mediaProgress;
        void media.play().catch(handleError);
      } catch (error) {
        handleError(error);
      }
    } else if (globalThis.speechSynthesis && typeof SpeechSynthesisUtterance !== "undefined") {
      const candidates = [options.language, ...(options.languageFallbacks ?? [])]
        .flatMap((value) => value.includes("-") ? [value, value.split("-")[0]!] : [value])
        .concat("")
        .filter((value, index, values) => value !== undefined && values.indexOf(value) === index);
      languageCandidates = candidates.length ? candidates : [""];
      startUtterance();
    } else {
      finish(new SpeechPlaybackError("SPEECH_VOICE_UNAVAILABLE"));
    }
  }

  return {
    done,
    stop: cancel,
    pause() {
      if (finished || paused) return;
      paused = true;
      if (startTimeout !== null) clearTimeout(startTimeout);
      startTimeout = null;
      suspendClock();
      report();
      if (media) media.pause();
      else globalThis.speechSynthesis?.pause();
    },
    resume() {
      if (finished || !paused) return;
      paused = false;
      waitForPlayback();
      if (media) void media.play().catch(handleError);
      else { globalThis.speechSynthesis?.resume(); playing(); }
    },
    setVolume(value: number) {
      if (finished || !Number.isFinite(value) || value < 0 || value > 1) return;
      if (media) media.volume = value;
      if (utterance) utterance.volume = value;
    },
    getActiveSeconds: activeSeconds,
    isMedia: Boolean(media),
  };
}
