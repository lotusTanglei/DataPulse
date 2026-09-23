<script setup lang="ts">
import { Pause, Play, RotateCcw, Square, UserRound, Volume2, VolumeX } from "@lucide/vue";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import type { DigitalHumanSpec } from "@datapulse/schema";
import type { JsonValue, QueryResult } from "../../query/types";
import type { ComponentInstance, ComponentQueryState, LoadAsset, RuntimeMode } from "../types";
import { pageSpeechQueue } from "../speechQueue";
import { createSpeechPlayback, SpeechPlaybackError } from "../speechPlayback";
import type { SpeechEvent } from "../speechProtocol";
import { buildSpeechPlan, canTransitionSpeechStatus, digitalHumanConfig, evaluateSpeechConditions, isWithinSpeechWindow, resolveSpeechRecording, type DigitalHumanStatus, type SpeechSource } from "./digitalHuman";

const props = withDefaults(defineProps<{
  instance: ComponentInstance;
  result: QueryResult | null;
  loading: boolean;
  error: unknown | null;
  loadAsset: LoadAsset;
  dataStates?: Record<string, ComponentQueryState>;
  mode?: RuntimeMode;
  parameters?: Record<string, JsonValue>;
  parameterSource?: "runtime" | "host";
  queryUpdatedAt?: number;
}>(), { mode: "preview", dataStates: () => ({}), parameters: () => ({}) });

const emit = defineEmits<{
  speechEvent: [event: SpeechEvent];
}>();
const config = computed(() => digitalHumanConfig(props.instance));
const plan = computed(() => buildSpeechPlan(props.instance, {
  result: props.result, status: props.loading ? "loading" : props.error ? "error" : props.result ? "success" : "idle",
  error: props.error, updatedAt: props.queryUpdatedAt,
}, props.dataStates));
const status = ref<DigitalHumanStatus>("idle");
const code = ref<string | null>(null);
const taskId = ref<string | null>(null);
const taskSource = ref<SpeechSource>("initial");
let taskRequestId = "";
let startedTaskId: string | null = null;
let lastSubtitleIndex = -1;
const muted = ref(config.value.muted || props.mode === "embed");
const volume = ref(config.value.volume);
const subtitleVisible = ref(config.value.subtitle_enabled);
const assets = ref({ avatar: "", speaking: "", audio: "" });
const mappedAssets = ref<Record<string, string>>({});
const actionAssets = ref<Record<string, { url: string; kind: "image" | "video" }>>({});
const activeAction = ref<{ url: string; kind: "image" | "video" } | null>(null);
let actionTimer: number | null = null;
const mediaLoading = ref(false);
const mediaCode = ref<string | null>(null);
const elapsed = ref(0);
const mediaDuration = ref<number | null>(null);
const boundaryIndex = ref<number | null>(null);
const taskCues = ref<NonNullable<NonNullable<DigitalHumanSpec["recording"]>["cues"]>>([]);
const speechVideo = ref<HTMLVideoElement | null>(null);
const activeVideo = ref(false);
let mutedSpeechPaused = false;
const taskText = ref("");
const owner = crypto.randomUUID();
const queuedIds = new Set<string>();
let generation = 0;
let disposed = false;
let assetController: AbortController | null = null;
let playback: ReturnType<typeof createSpeechPlayback> | null = null;
let monitor: ReturnType<typeof setInterval> | null = null;
let previousValues = "";
let hasInitial = false;
let aboveThreshold: boolean | null = null;
let groupedConditionState: boolean | null = null;
let pendingCondition: { value: boolean; since: number } | null = null;
let lastStarted = -Infinity;
let lastDataAt = Date.now();
let lastIntervalAt = Date.now();
let dailyCount = 0;
let pendingParameterTrigger = false;
let dailySeconds = 0;
let day = "";
let quietRetryTimer: number | null = null;
const trigger = computed(() => config.value.trigger);
const subtitle = computed(() => taskText.value || plan.value.text);
const visual = computed(() => {
  const speaking = config.value.speech_source !== "video" && ["speaking", "paused"].includes(status.value) && assets.value.speaking;
  return { source: speaking ? assets.value.speaking : assets.value.avatar, kind: speaking ? config.value.speaking_kind : config.value.avatar_kind };
});
const stateLabels: Record<DigitalHumanStatus, string> = {
  disabled: "已关闭", idle: "待机", loading_data: "数据加载中", ready: "就绪", queued: "等待播报",
  preparing_media: "媒体准备中", speaking: "播报中", paused: "已暂停", muted: "已静音",
  waiting_gesture: "等待启用声音", fallback: "文字播报", error: "播报失败",
};
const failureCode = computed(() => code.value ?? plan.value.code ?? mediaCode.value);
const estimatedDuration = computed(() => Math.max(1, subtitle.value.length / (5 * config.value.rate)));
const progress = computed(() => Math.min(100, elapsed.value / (mediaDuration.value ?? estimatedDuration.value) * 100));
const subtitleFontSize = computed(() => Math.min(80, Math.max(12, Number(config.value.subtitle_font_size) || 20)));
const subtitleMaxLines = computed(() => Math.min(10, Math.max(1, Math.floor(Number(config.value.subtitle_max_lines) || 3))));
const sentences = computed(() => taskCues.value.length ? taskCues.value.map((cue) => cue.text)
  : subtitle.value.match(/[^。！？.!?\n]+[。！？.!?\n]*/g) ?? [subtitle.value]);
const currentSentence = computed(() => {
  if (taskCues.value.length) return taskCues.value.findIndex((cue) => elapsed.value >= cue.start && elapsed.value < cue.end);
  if (boundaryIndex.value !== null) {
    let offset = 0;
    return sentences.value.findIndex((sentence) => { offset += sentence.length; return boundaryIndex.value! < offset; });
  }
  return Math.min(sentences.value.length - 1, Math.floor(elapsed.value / (mediaDuration.value ?? estimatedDuration.value) * sentences.value.length));
});

function emitLifecycle(
  name: SpeechEvent["name"],
  outcome?: SpeechEvent["outcome"],
  cue?: { index: number; text: string; start: number | null; end: number | null },
): void {
  if (disposed) return;
  emit("speechEvent", {
    name, ...(outcome ? { outcome } : {}),
    component_id: props.instance.id, task_id: taskId.value, status: status.value, source: taskSource.value,
    code: code.value, request_id: taskRequestId || plan.value.requestId, timestamp: Date.now(),
    ...(cue ? { cue_index: cue.index, cue_text: cue.text, cue_start: cue.start, cue_end: cue.end } : {}),
  });
}

function setStatus(next: DigitalHumanStatus, reason: string | null = null): void {
  if (disposed || (status.value === next && code.value === reason)) return;
  if (!canTransitionSpeechStatus(status.value, next)) {
    code.value = "SPEECH_INVALID_STATE_TRANSITION";
    emitLifecycle("speechError");
    return;
  }
  status.value = next;
  code.value = reason;
  emitLifecycle("statusChange");
  if (next === "fallback") emitLifecycle("fallback");
  if (next === "waiting_gesture") emitLifecycle("userGestureRequired");
}

function endSpeech(outcome: SpeechEvent["outcome"]): void {
  if (startedTaskId && startedTaskId === taskId.value) {
    emitLifecycle("speechEnd", outcome);
    startedTaskId = null;
  }
}

function stop(): void {
  if (actionTimer !== null) {
    window.clearTimeout(actionTimer);
    actionTimer = null;
  }
  activeAction.value = null;
  if (quietRetryTimer !== null) {
    window.clearTimeout(quietRetryTimer);
    quietRetryTimer = null;
  }
  if (!disposed) setStatus(config.value.enabled ? "idle" : "disabled");
  endSpeech("stopped");
  generation++;
  pageSpeechQueue.cancel(owner);
  queuedIds.clear();
  playback?.stop();
  playback = null;
  taskId.value = null;
  taskRequestId = "";
  taskText.value = "";
  elapsed.value = 0;
  mediaDuration.value = null;
  boundaryIndex.value = null;
  taskCues.value = [];
  lastSubtitleIndex = -1;
  activeVideo.value = false;
  mutedSpeechPaused = false;
  if (!disposed) setStatus(config.value.enabled ? "idle" : "disabled");
}

function scheduleQuietRetry(source: SpeechSource): void {
  if (quietRetryTimer !== null || disposed) return;
  quietRetryTimer = window.setTimeout(() => {
    quietRetryTimer = null;
    if (quietHours()) scheduleQuietRetry(source);
    else speak(source);
  }, 60_000);
}

function release(url: string): void {
  if (url.startsWith("blob:")) URL.revokeObjectURL(url);
}

async function loadAssets(): Promise<void> {
  stop();
  assetController?.abort();
  const controller = new AbortController();
  assetController = controller;
  for (const url of [
    ...Object.values(assets.value),
    ...Object.values(mappedAssets.value),
    ...Object.values(actionAssets.value).map((item) => item.url),
  ]) release(url);
  assets.value = { avatar: "", speaking: "", audio: "" };
  mappedAssets.value = {};
  actionAssets.value = {};
  mediaCode.value = null;
  const entries = [
    ["avatar", config.value.avatar_asset_id], ["speaking", config.value.speaking_asset_id], ["audio", config.value.audio_asset_id],
    ...config.value.recordings.map((recording) => [recording.asset_id, recording.asset_id] as const),
    ...(config.value.recording ? [[config.value.recording.asset_id, config.value.recording.asset_id] as const] : []),
    ...config.value.actions.map((action) => [`action:${action.id}`, action.asset_id] as const),
  ].filter((entry, index, all) => Boolean(entry[1]) && all.findIndex((candidate) => candidate[0] === entry[0]) === index);
  mediaLoading.value = entries.some(([, id]) => Boolean(id));
  const timeout = setTimeout(() => controller.abort(), 10000);
  const results = await Promise.allSettled(entries.map(async ([kind, id]) => {
    if (!id) return;
    const url = await props.loadAsset(id, controller.signal);
    if (disposed || controller.signal.aborted || controller !== assetController) {
      release(url);
      return;
    }
    if (kind === "avatar" || kind === "speaking" || kind === "audio") {
      assets.value = { ...assets.value, [kind]: url };
    } else if (kind.startsWith("action:")) {
      const action = config.value.actions.find((item) => `action:${item.id}` === kind);
      if (action) {
        actionAssets.value = {
          ...actionAssets.value,
          [action.id]: { url, kind: action.asset_kind ?? "image" },
        };
      }
    } else {
      mappedAssets.value = { ...mappedAssets.value, [kind]: url };
    }
  }));
  clearTimeout(timeout);
  if (!disposed && controller === assetController) {
    mediaLoading.value = false;
    if (results.some((result) => result.status === "rejected") || controller.signal.aborted) {
      mediaCode.value = "SPEECH_ASSET_UNAVAILABLE";
    }
    await nextTick();
    considerAutomatic();
  }
}

function activateAction(): void {
  const action = [...config.value.actions].sort((left, right) =>
    (right.priority ?? 0) - (left.priority ?? 0) || left.id.localeCompare(right.id),
  ).find((item) =>
    (!item.conditions?.length || evaluateSpeechConditions(
      item.conditions,
      item.condition_mode ?? "all",
      plan.value.values,
    )) && actionAssets.value[item.id],
  );
  if (!action) return;
  if (actionTimer !== null) window.clearTimeout(actionTimer);
  activeAction.value = actionAssets.value[action.id] ?? null;
  actionTimer = window.setTimeout(() => {
    activeAction.value = null;
    actionTimer = null;
  }, action.duration_ms);
}

function quietHours(): boolean {
  if (!config.value.quiet_start || !config.value.quiet_end) return false;
  const time = new Intl.DateTimeFormat("en-GB", { timeZone: config.value.timezone, hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(new Date());
  const start = config.value.quiet_start;
  const end = config.value.quiet_end;
  return start <= end ? time >= start && time < end : time >= start || time < end;
}

function triggerWindowOpen(): boolean {
  return isWithinSpeechWindow(
    trigger.value.window_start,
    trigger.value.window_end,
    config.value.timezone,
  );
}

function speak(source: SpeechSource = "manual"): void {
  if (!config.value.enabled || disposed) return;
  if (plan.value.loading) { setStatus("loading_data"); return; }
  if (plan.value.code) { setStatus("fallback", plan.value.code); return; }
  if (mediaLoading.value) { setStatus("preparing_media"); return; }
  if (Date.now() - lastDataAt > config.value.stale_after_seconds * 1000 && plan.value.values.size) {
    setStatus("fallback", "SPEECH_DATA_STALE"); return;
  }
  taskSource.value = source;
  if (quietHours()) {
    if (config.value.quiet_mode === "subtitle") {
      taskText.value = plan.value.text;
      setStatus("fallback", "SPEECH_QUIET_HOURS_SUBTITLE");
    } else {
      if (config.value.quiet_mode === "delay") scheduleQuietRetry(source);
      setStatus("muted", config.value.quiet_mode === "delay" ? "SPEECH_QUIET_HOURS_DELAY" : "SPEECH_QUIET_HOURS");
    }
    return;
  }
  if (muted.value || !config.value.voice_enabled) { setStatus(muted.value ? "muted" : "fallback"); return; }
  const currentDay = new Intl.DateTimeFormat("en-CA", { timeZone: config.value.timezone }).format(new Date());
  if (currentDay !== day) { day = currentDay; dailyCount = 0; dailySeconds = 0; }
  if (dailyCount >= config.value.daily_max_count || dailySeconds >= config.value.daily_max_seconds) {
    setStatus("fallback", "SPEECH_DAILY_LIMIT"); return;
  }
  if (Date.now() - lastStarted < (trigger.value.cooldown_seconds ?? 30) * 1000) return;
  lastStarted = Date.now();
  const taskGeneration = generation;
  const id = crypto.randomUUID();
  const text = plan.value.text;
  const requestId = plan.value.requestId;
  queuedIds.add(id);
  const accepted = pageSpeechQueue.enqueue({
    id, owner, expiresAt: Date.now() + config.value.task_ttl_seconds * 1000,
    priority: source === "threshold" ? config.value.trigger.priority ?? 0 : 0,
    cancel() {
      queuedIds.delete(id);
      if (generation === taskGeneration && (taskId.value === id || (!queuedIds.size && !playback))) {
        setStatus("idle");
        if (taskId.value === id) endSpeech("cancelled");
      }
    },
    async run(signal) {
      queuedIds.delete(id);
      if (signal.aborted || disposed || taskGeneration !== generation) return;
      if (muted.value || quietHours()) { setStatus("muted"); return; }
      if (dailyCount >= config.value.daily_max_count || dailySeconds >= config.value.daily_max_seconds) {
        setStatus("fallback", "SPEECH_DAILY_LIMIT"); return;
      }
      taskId.value = id;
      taskRequestId = requestId;
      taskSource.value = source;
      taskText.value = text;
      lastSubtitleIndex = -1;
      elapsed.value = 0;
      boundaryIndex.value = null;
      const selected = resolveSpeechRecording(config.value, text, plan.value.values);
      let mediaUrl = selected.recording
        ? mappedAssets.value[selected.recording.asset_id] ?? ""
        : selected.kind === "video" ? assets.value.speaking : selected.kind === "audio" ? assets.value.audio : "";
      let fallbackCode = selected.code;
      if (selected.kind !== "browser" && (!mediaUrl || (selected.kind === "video" && !speechVideo.value))) {
        fallbackCode = "SPEECH_ASSET_UNAVAILABLE";
        mediaUrl = "";
      }
      activeVideo.value = selected.kind === "video" && Boolean(mediaUrl);
      taskCues.value = mediaUrl ? selected.recording?.cues ?? [] : [];
      mediaDuration.value = mediaUrl ? selected.recording?.duration_seconds ?? null : null;
      if (fallbackCode) setStatus("fallback", fallbackCode);
      setStatus("preparing_media", fallbackCode);
      let driverActiveSeconds = 0;
      let driver = createSpeechPlayback({
        text, audioUrl: mediaUrl, language: config.value.language,
        languageFallbacks: [config.value.language.split("-")[0] ?? ""], rate: config.value.rate,
        ...(activeVideo.value && speechVideo.value ? { mediaElement: speechVideo.value } : {}),
        pitch: config.value.pitch, volume: volume.value,
        maxSeconds: Math.min(config.value.max_duration_seconds, config.value.daily_max_seconds - dailySeconds),
      }, signal, () => {
        if (!signal.aborted && generation === taskGeneration) {
          if (startedTaskId !== id) dailyCount++;
          activateAction();
          startedTaskId = id;
          setStatus("speaking", fallbackCode);
          emitLifecycle("speechStart");
        }
      }, (timeline) => {
        if (signal.aborted || generation !== taskGeneration || disposed) return;
        elapsed.value = timeline.currentSeconds;
        if (timeline.durationSeconds !== null) mediaDuration.value = timeline.durationSeconds;
        boundaryIndex.value = timeline.charIndex;
      });
      playback = driver;
      try {
        await driver.done;
        if (!signal.aborted && generation === taskGeneration) {
          setStatus("idle");
          endSpeech("completed");
        }
      } catch (error) {
        if (!signal.aborted && generation === taskGeneration) {
          const failure = error instanceof SpeechPlaybackError ? error.code : "SPEECH_MEDIA_FAILED";
          const canFallbackToBrowser = Boolean(mediaUrl) && ["SPEECH_MEDIA_FAILED", "SPEECH_MEDIA_STALLED"].includes(failure);
          if (canFallbackToBrowser) {
            driverActiveSeconds += driver.getActiveSeconds();
            fallbackCode = failure;
            activeVideo.value = false;
            taskCues.value = [];
            mediaDuration.value = null;
            setStatus("fallback", failure);
            driver = createSpeechPlayback({
              text,
              audioUrl: "",
              language: config.value.language,
              languageFallbacks: [config.value.language.split("-")[0] ?? ""],
              rate: config.value.rate,
              pitch: config.value.pitch,
              volume: volume.value,
              maxSeconds: Math.min(config.value.max_duration_seconds, config.value.daily_max_seconds - dailySeconds),
            }, signal, () => {
              if (!signal.aborted && generation === taskGeneration) {
                if (startedTaskId !== id) dailyCount++;
                activateAction();
                startedTaskId = id;
                setStatus("speaking", fallbackCode);
                emitLifecycle("speechStart");
              }
            }, (timeline) => {
              if (signal.aborted || generation !== taskGeneration || disposed) return;
              elapsed.value = timeline.currentSeconds;
              boundaryIndex.value = timeline.charIndex;
            });
            playback = driver;
            try {
              await driver.done;
              if (!signal.aborted && generation === taskGeneration) {
                setStatus("idle");
                endSpeech("completed");
              }
            } catch (browserError) {
              if (!signal.aborted && generation === taskGeneration) {
                const browserFailure = browserError instanceof SpeechPlaybackError ? browserError.code : "SPEECH_VOICE_UNAVAILABLE";
                setStatus(browserFailure === "SPEECH_GESTURE_REQUIRED" ? "waiting_gesture" : "fallback", browserFailure);
                emitLifecycle("speechError");
                startedTaskId = null;
              }
            }
          } else {
            setStatus(failure === "SPEECH_GESTURE_REQUIRED" || failure === "SPEECH_START_TIMEOUT" ? "waiting_gesture" : "fallback", failure);
            emitLifecycle("speechError");
            startedTaskId = null;
          }
        }
      } finally {
        dailySeconds += driverActiveSeconds + driver.getActiveSeconds();
        if (playback === driver) { playback = null; activeVideo.value = false; mutedSpeechPaused = false; }
        if (taskId.value === id) {
          taskId.value = null;
          taskRequestId = "";
        }
      }
    },
  }, config.value.queue_policy, config.value.max_queue_length);
  if (accepted && !playback) setStatus("queued");
  if (!accepted) { queuedIds.delete(id); setStatus("fallback", "SPEECH_QUEUE_FULL"); }
}

function groupedConditionTriggered(): boolean {
  const conditions = trigger.value.conditions ?? [];
  if (!conditions.length) return false;
  const next = evaluateSpeechConditions(conditions, trigger.value.condition_mode ?? "all", plan.value.values);
  if (groupedConditionState === null) {
    groupedConditionState = next;
    pendingCondition = null;
    return false;
  }
  if (next !== groupedConditionState) {
    if (!pendingCondition || pendingCondition.value !== next) {
      pendingCondition = { value: next, since: Date.now() };
    }
    if (Date.now() - pendingCondition.since < (trigger.value.debounce_seconds ?? 0) * 1000) return false;
    const previous = groupedConditionState;
    groupedConditionState = next;
    pendingCondition = null;
    return next
      ? trigger.value.edge === "enter" || trigger.value.edge === "both"
      : trigger.value.edge === "recover" || trigger.value.edge === "both";
  }
  pendingCondition = null;
  return false;
}

function visualFailed(): void {
  const slot = ["speaking", "paused"].includes(status.value) && assets.value.speaking ? "speaking" : "avatar";
  release(assets.value[slot]);
  assets.value = { ...assets.value, [slot]: "" };
  mediaCode.value = "SPEECH_ASSET_UNAVAILABLE";
}

function pause(): void {
  if (!playback || status.value !== "speaking") return;
  playback.pause();
  setStatus("paused", code.value);
}

function play(source: SpeechSource = "manual"): void {
  if (playback && status.value === "paused") {
    if (!mutedSpeechPaused) playback.resume();
    setStatus("speaking", code.value);
  } else {
    if (source === "manual" && (status.value === "waiting_gesture" || status.value === "fallback")) lastStarted = -Infinity;
    speak(source);
  }
}

function setMuted(value: boolean): void {
  muted.value = value;
  playback?.setVolume(value ? 0 : volume.value);
  // Browser synthesis cannot reliably change the active utterance volume. Pause it without cancelling.
  if (playback && !playback.isMedia) {
    if (value) { mutedSpeechPaused = true; playback.pause(); }
    else if (mutedSpeechPaused) {
      mutedSpeechPaused = false;
      if (status.value !== "paused") playback.resume();
    }
  }
  if (!playback) setStatus(value ? "muted" : "ready");
  else emitLifecycle("statusChange");
}

function setVolume(value: number): void {
  if (!Number.isFinite(value) || value < 0 || value > 1) return;
  volume.value = value;
  playback?.setVolume(muted.value ? 0 : value);
}

function handleKeyboard(event: KeyboardEvent): void {
  // Keep shortcuts scoped to the focusable region; native controls retain their own keys.
  if (event.target !== event.currentTarget) return;
  const key = event.key.toLowerCase();
  if (key === " " || key === "enter") {
    event.preventDefault();
    status.value === "speaking" ? pause() : play();
  } else if (key === "m") {
    event.preventDefault();
    setMuted(!muted.value);
  } else if (key === "c") {
    event.preventDefault();
    subtitleVisible.value = !subtitleVisible.value;
  } else if (key === "escape") {
    event.preventDefault();
    stop();
  }
}

function considerAutomatic(): void {
  if (disposed) return;
  if (!config.value.enabled) { stop(); setStatus("disabled"); return; }
  if (plan.value.loading) { stop(); setStatus("loading_data"); return; }
  if (plan.value.code) { stop(); setStatus("fallback", plan.value.code); return; }
  if (mediaLoading.value) { setStatus("preparing_media"); return; }
  const first = !hasInitial;
  const changed = previousValues !== plan.value.fingerprint;
  const oldValues = new Map<string, JsonValue>(previousValues ? JSON.parse(previousValues) : []);
  previousValues = plan.value.fingerprint;
  hasInitial = true;
  if (plan.value.updatedAt !== null) lastDataAt = plan.value.updatedAt;
  if (!config.value.auto_play || props.mode === "editor") { if (!playback) setStatus("ready"); return; }
  if (!triggerWindowOpen()) return;
  const kind = trigger.value.kind;
  if (pendingParameterTrigger) {
    pendingParameterTrigger = false;
    speak("parameter");
  }
  if (first && (kind === "initial" || kind === "data_change")) speak("initial");
  else if (kind === "data_change" && changed) {
    const min = trigger.value.min_change ?? 0;
    const significant = !min || [...plan.value.values].some(([name, value]) => {
      const previous = oldValues.get(name);
      return typeof value === "number" && typeof previous === "number" && Math.abs(value - previous) >= min;
    });
    if (significant) speak("data_change");
  }
  if (kind === "ranking_change" || kind === "status_change") {
    if (!changed || !trigger.value.variable) return;
    const previous = oldValues.get(trigger.value.variable);
    const current = plan.value.values.get(trigger.value.variable);
    if (current === undefined || previous === undefined) return;
    if (kind === "ranking_change" && (typeof current !== "number" || typeof previous !== "number" || current === previous)) return;
    if (kind === "status_change" && JSON.stringify(current) === JSON.stringify(previous)) return;
    speak(kind);
    return;
  }
  if (kind === "threshold") {
    if (trigger.value.conditions?.length) {
      if (groupedConditionTriggered()) speak("threshold");
      return;
    }
    if (!trigger.value.variable) return;
    const value = plan.value.values.get(trigger.value.variable);
    if (typeof value !== "number") return;
    const crossed = trigger.value.direction === "below" ? value < trigger.value.threshold! : value > trigger.value.threshold!;
    const prior = aboveThreshold;
    aboveThreshold = crossed;
    if (prior !== null && prior !== crossed && (trigger.value.edge === "both" || (crossed ? trigger.value.edge !== "recover" : trigger.value.edge === "recover"))) speak("threshold");
  }
}

watch(() => [
  config.value.avatar_asset_id,
  config.value.speaking_asset_id,
  config.value.audio_asset_id,
  JSON.stringify(config.value.recordings),
  config.value.recording?.asset_id ?? "",
  props.loadAsset,
], () => void loadAssets(), { immediate: true });
watch(() => props.instance.props, () => {
  stop();
  muted.value = config.value.muted || props.mode === "embed";
  volume.value = config.value.volume;
  subtitleVisible.value = config.value.subtitle_enabled;
  hasInitial = false;
  aboveThreshold = null;
  groupedConditionState = null;
  pendingCondition = null;
  considerAutomatic();
}, { deep: true });
watch(plan, () => {
  if (plan.value.loading || previousValues !== plan.value.fingerprint || plan.value.code) stop();
  considerAutomatic();
}, { immediate: true });
watch([currentSentence, status], ([index, nextStatus]) => {
  if (!(nextStatus === "speaking" || nextStatus === "paused") || index < 0 || index === lastSubtitleIndex) return;
  lastSubtitleIndex = index;
  const cue = taskCues.value[index];
  emitLifecycle("subtitleCue", undefined, {
    index,
    text: sentences.value[index] ?? "",
    start: cue?.start ?? null,
    end: cue?.end ?? null,
  });
});
watch(() => props.parameters, (next, previous) => {
  const name = trigger.value.parameter;
  if (trigger.value.kind === "parameter" && name && JSON.stringify(next[name]) !== JSON.stringify(previous?.[name]) &&
    (trigger.value.include_host !== false || props.parameterSource !== "host") && config.value.auto_play && props.mode !== "editor") {
    // A parameter generation supersedes any active speech before enqueueing the new one.
    stop();
    lastStarted = -Infinity;
    pendingParameterTrigger = true;
    nextTick(considerAutomatic);
  }
}, { deep: true });

onMounted(() => {
  emitLifecycle("digitalHumanReady");
  monitor = setInterval(() => {
    if (plan.value.values.size && Date.now() - lastDataAt > config.value.stale_after_seconds * 1000) {
      if (code.value !== "SPEECH_DATA_STALE") { stop(); setStatus("fallback", "SPEECH_DATA_STALE"); }
      return;
    }
    if (config.value.auto_play && props.mode !== "editor" && trigger.value.kind === "interval" &&
      Date.now() - lastIntervalAt >= (trigger.value.interval_seconds ?? 30) * 1000) {
      lastIntervalAt = Date.now();
      speak("interval");
    }
    if (config.value.auto_play && props.mode !== "editor" && trigger.value.kind === "threshold" &&
      trigger.value.conditions?.length && pendingCondition && Date.now() - pendingCondition.since >= (trigger.value.debounce_seconds ?? 0) * 1000) {
      considerAutomatic();
    }
  }, 250);
});
onBeforeUnmount(() => {
  stop();
  disposed = true;
  assetController?.abort();
  if (monitor) clearInterval(monitor);
  for (const url of [...Object.values(assets.value), ...Object.values(mappedAssets.value)]) release(url);
  for (const { url } of Object.values(actionAssets.value)) release(url);
});
defineExpose({
  play, pause, stop, speak, mute: setMuted, setVolume,
  getStatus: () => ({ component_id: props.instance.id, status: status.value, code: failureCode.value, muted: muted.value, volume: volume.value }),
});
</script>

<template>
  <section class="digital-human" role="region" tabindex="0" aria-keyshortcuts="Space Enter M C Escape" :data-status="status" :data-muted="muted" :data-subtitle-position="config.subtitle_position" :aria-label="config.name" :aria-labelledby="config.show_identity ? `digital-human-${instance.id}-name` : undefined" :aria-describedby="`digital-human-${instance.id}-subtitle`" :lang="config.language" @keydown="handleKeyboard">
    <div class="digital-human__visual">
      <img v-if="visual.source && visual.kind === 'image'" v-show="!activeVideo" :src="visual.source" :alt="config.name"
        :style="{ objectFit: config.fit, transform: config.mirror ? 'scaleX(-1)' : undefined }"
        @error="visualFailed" />
      <video v-else-if="visual.source && visual.kind === 'video'" v-show="!activeVideo" :key="visual.source" :src="visual.source" muted playsinline autoplay loop
        :style="{ objectFit: config.fit, transform: config.mirror ? 'scaleX(-1)' : undefined }"
        @error="visualFailed" />
      <UserRound v-else v-show="!activeVideo" class="digital-human__placeholder" :size="96" :stroke-width="1" aria-hidden="true" />
      <video v-if="config.speech_source === 'video'" ref="speechVideo" v-show="activeVideo" class="digital-human__speech-video" playsinline preload="metadata"
        :style="{ objectFit: config.fit, transform: config.mirror ? 'scaleX(-1)' : undefined }" />
      <div v-if="activeAction" class="digital-human__action" aria-hidden="true">
        <video v-if="activeAction.kind === 'video'" :src="activeAction.url" autoplay muted playsinline />
        <img v-else :src="activeAction.url" alt="" />
      </div>
      <span v-if="config.show_status" :id="`digital-human-${instance.id}-status`" class="digital-human__status" role="status" aria-live="polite" aria-atomic="true">{{ stateLabels[status] }}{{ muted && status !== 'muted' ? ' · 已静音' : '' }}</span>
      <div v-if="status === 'speaking' && config.animation" class="digital-human__activity" aria-hidden="true"><i /><i /><i /><i /><i /></div>
    </div>
    <header v-if="config.show_identity" class="digital-human__identity">
      <strong :id="`digital-human-${instance.id}-name`">{{ config.name }}</strong><span v-if="config.role">{{ config.role }}</span>
    </header>
    <div v-if="subtitleVisible" :id="`digital-human-${instance.id}-subtitle`" class="digital-human__subtitle" :class="{ 'is-scrollable': config.subtitle_scroll === 'scroll' }" :style="{ color: config.subtitle_color, backgroundColor: config.subtitle_background, fontSize: subtitleFontSize + 'px', maxHeight: (subtitleMaxLines * 1.5 + 0.8) + 'em' }" role="log" tabindex="0" aria-label="字幕" aria-live="polite" aria-atomic="true" aria-relevant="additions text">
      <template v-if="failureCode === 'SPEECH_DATA_STALE'">{{ config.stale_text }}</template>
      <template v-else><span v-for="(sentence, index) in sentences" :key="index" :class="{ 'is-current': status === 'speaking' && index === currentSentence }">{{ sentence }}</span></template>
    </div>
    <span v-else :id="`digital-human-${instance.id}-subtitle`" class="digital-human__sr-subtitle" role="status" aria-label="字幕" aria-live="polite" aria-atomic="true">{{ failureCode === 'SPEECH_DATA_STALE' ? config.stale_text : subtitle }}</span>
    <div v-if="config.show_controls" class="digital-human__controls">
      <button type="button" :title="status === 'speaking' ? '暂停播报' : '播放播报'" :aria-label="status === 'speaking' ? '暂停播报' : '播放播报'"
        :disabled="!config.enabled || plan.loading || mediaLoading"
        @click.stop="status === 'speaking' ? pause() : play()"><Pause v-if="status === 'speaking'" :size="16" /><Play v-else :size="16" /></button>
      <button type="button" title="停止播报" aria-label="停止播报" @click.stop="stop"><Square :size="16" /></button>
      <button type="button" title="重新播报" aria-label="重新播报" @click.stop="stop(); lastStarted = -Infinity; speak()"><RotateCcw :size="16" /></button>
      <button type="button" :title="muted ? '启用声音' : '静音'" :aria-label="muted ? '启用声音' : '静音'"
        :aria-pressed="muted" @click.stop="setMuted(!muted); !muted && !playback && play()"><VolumeX v-if="muted" :size="16" /><Volume2 v-else :size="16" /></button>
      <input type="range" min="0" max="1" step="0.05" :value="volume" :aria-valuenow="volume" aria-valuemin="0" aria-valuemax="1" aria-label="播报音量"
        @input="setVolume(Number(($event.target as HTMLInputElement).value))" @pointerdown.stop />
      <label class="digital-human__captions"><input v-model="subtitleVisible" type="checkbox" />字幕</label>
    </div>
    <div v-if="status === 'speaking' || status === 'paused'" class="digital-human__progress" role="progressbar" aria-label="播报进度" :aria-valuenow="Math.round(progress)" :aria-valuetext="`${Math.round(progress)}%`" aria-valuemin="0" aria-valuemax="100"><i :style="{ width: progress + '%' }" /></div>
    <small v-if="failureCode" class="digital-human__notice" role="alert" aria-live="assertive">{{ failureCode }}<span v-if="plan.requestId"> · {{ plan.requestId }}</span></small>
  </section>
</template>

<style scoped>
.digital-human { display: flex; flex-direction: column; box-sizing: border-box; width: 100%; height: 100%; min-width: 0; overflow: hidden; color: var(--screen-component-text, var(--screen-text-primary, #edf7ff)); background: var(--screen-component-surface, transparent); }
.digital-human__visual { position: relative; flex: 1; min-height: 0; display: grid; place-items: center; overflow: hidden; }
.digital-human__action { position: absolute; inset: 0; z-index: 2; display: grid; place-items: center; pointer-events: none; }
.digital-human__action img, .digital-human__action video { position: absolute; width: 100%; height: 100%; object-fit: contain; }
.digital-human__visual img, .digital-human__visual video { position: absolute; width: 100%; height: 100%; }
.digital-human__placeholder { max-width: 60%; max-height: 70%; color: var(--screen-accent, #26d9c1); }
.digital-human__status { position: absolute; right: 8px; top: 8px; max-width: calc(100% - 16px); padding: 3px 6px; border-radius: 4px; color: #f1f5f9; background: rgb(0 0 0 / 72%); font-size: 12px; overflow-wrap: anywhere; }
.digital-human__identity { display: flex; flex-wrap: wrap; gap: 4px 8px; padding: 6px 10px; overflow-wrap: anywhere; }
.digital-human__identity strong { font-size: 16px; }
.digital-human__identity span { color: var(--screen-component-text, var(--screen-text-secondary, #9ab3c8)); font-size: 13px; }
.digital-human__subtitle { flex: none; box-sizing: border-box; padding: 6px 10px; overflow: auto; color: #fff; background: rgb(0 0 0 / 80%); line-height: 1.5; overflow-wrap: anywhere; user-select: text; }
.digital-human__subtitle:focus-visible { outline: 2px solid var(--screen-accent, #26d9c1); outline-offset: -2px; }
.digital-human__subtitle.is-scrollable { overflow-y: auto; scrollbar-width: thin; }
.digital-human[data-subtitle-position="top"] .digital-human__subtitle { order: -1; }
.digital-human__subtitle .is-current { text-decoration: underline; text-underline-offset: 4px; }
.digital-human__sr-subtitle { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
.digital-human__controls { display: flex; flex-wrap: wrap; align-items: center; gap: 3px; padding: 5px 8px; flex: none; }
.digital-human__controls button { display: grid; place-items: center; width: 28px; height: 28px; padding: 0; border: 1px solid var(--screen-panel-border, #52606b); border-radius: 4px; color: inherit; background: transparent; cursor: pointer; }
.digital-human__controls button:disabled { opacity: 0.5; cursor: default; }
.digital-human__controls button:focus-visible { outline: 2px solid var(--screen-accent, #26d9c1); outline-offset: 1px; }
.digital-human__controls input[type="range"] { width: 50px; min-width: 30px; height: 28px; min-height: 0; padding: 0; border: 0; background: transparent; box-shadow: none; flex: 1; max-width: 120px; accent-color: var(--screen-accent, #26d9c1); }
.digital-human__captions { display: inline-flex; flex: none; gap: 4px; align-items: center; white-space: nowrap; font-size: 12px; }
.digital-human__captions input[type="checkbox"] { width: 14px; height: 14px; min-height: 0; padding: 0; margin: 0; flex: none; accent-color: var(--screen-accent, #26d9c1); }
.digital-human__notice { display: block; max-height: 42px; overflow: auto; padding: 2px 8px 5px; color: #ffd175; font-size: 10px; overflow-wrap: anywhere; }
.digital-human__progress { flex: none; height: 3px; background: rgb(255 255 255 / 12%); }
.digital-human__progress i { display: block; height: 100%; background: var(--screen-accent, #26d9c1); }
.digital-human__activity { position: absolute; bottom: 10px; display: flex; align-items: center; gap: 4px; height: 22px; }
.digital-human__activity i { width: 3px; height: 16px; background: var(--screen-accent, #26d9c1); animation: speaking 800ms infinite alternate; }
.digital-human__activity i:nth-child(even) { animation-delay: 250ms; }
.digital-human__activity i:nth-child(3) { animation-delay: 400ms; }
@keyframes speaking { from { transform: scaleY(0.3); } to { transform: scaleY(1); } }
@media (prefers-reduced-motion: reduce) { .digital-human__activity i { animation: none; } }
</style>
