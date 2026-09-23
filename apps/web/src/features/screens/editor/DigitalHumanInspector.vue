<script setup lang="ts">
import { FolderOpen, Pencil, Plus, Sparkles, Trash2, Upload, Volume2 } from "@lucide/vue";
import type { DigitalHumanBinding, DigitalHumanTrigger } from "@datapulse/schema";
import type { DigitalHumanSpec } from "@datapulse/schema";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { ApiError, apiRequest } from "../../../lib/api";
import type { ComponentInstance } from "../../runtime/types";
import type { JsonValue, QueryResult } from "../../query/types";
import { buildSpeechPlan, digitalHumanConfig, parseSpeechTemplate, sensitiveSpeechField } from "../../runtime/builtins/digitalHuman";
import { createMockBinding, resolveLocalResult } from "../../runtime/mockData";
import { queryScreenDocument } from "../api";
import AssetLibraryDialog from "../assets/AssetLibraryDialog.vue";
import SpeechRecordingEditor from "./SpeechRecordingEditor.vue";
import { assetUrl, getAsset, listAssets, uploadAsset, type AssetType, type ScreenAsset } from "../assets/api";
import {
  createDigitalHumanSpeechPlan,
  getDigitalHumanSpeechTask,
  listDigitalHumanProviderDirectory,
  type DigitalHumanProviderChoice,
  queueDigitalHumanSpeechTask,
} from "../../settings/api";
import type { SpeechTask } from "../../settings/types";
import { useScreenEditorStore } from "./store";

const props = defineProps<{ instance: ComponentInstance }>();
const store = useScreenEditorStore();
const config = computed(() => digitalHumanConfig(props.instance));
const error = ref("");
const pending = ref(false);
const componentId = ref("");
const field = ref("");
const variableName = ref("value");
const fieldNames = ref<string[]>([]);
const fieldLoading = ref(false);
const currentPreviewResult = ref<QueryResult | null>(null);
const previewMode = ref<"demo" | "current" | "threshold">("demo");
const previewNotice = ref("");
let previewUtterance: SpeechSynthesisUtterance | null = null;
const controller = new AbortController();
let fieldController: AbortController | null = null;
const assets = ref<ScreenAsset[]>([]);
const soundOpen = ref(false);
const recordingAsset = computed(() => assets.value.find((asset) => asset.id === (
  config.value.speech_source === "video" ? config.value.speaking_asset_id
    : config.value.speech_source !== "browser" ? config.value.audio_asset_id : ""
)) ?? null);
type Recording = NonNullable<DigitalHumanSpec["recording"]>;
type SpeechSegment = NonNullable<DigitalHumanSpec["speech_segments"]>[number];
type RecordingCondition = NonNullable<Recording["conditions"]>[number];
type Action = NonNullable<DigitalHumanSpec["actions"]>[number];
type ActionCondition = NonNullable<Action["conditions"]>[number];
const mappingAsset = ref<ScreenAsset | null>(null);
const mappingRecording = ref<Recording | null>(null);
const librarySlot = ref<string | null>(null);
const libraryTypes = computed<AssetType[]>(() => librarySlot.value === "mapped"
  ? ["audio", "video"]
  : (assetSlots.find((slot) => slot.key === librarySlot.value)?.types ?? []) as AssetType[]);
function assetReferences(value: unknown): string[] {
  if (!value || typeof value !== "object") return [];
  return Object.entries(value).flatMap(([key, nested]) =>
    (key === "asset_id" || key.endsWith("_asset_id")) && typeof nested === "string"
      ? [nested] : assetReferences(nested),
  );
}
const inUseIds = computed(() => assetReferences(store.document?.components));
watch(() => props.instance.id, () => { librarySlot.value = null; });
const sources = computed(() => (store.document?.components ?? []).filter(
  (item) => item.type !== "builtin.digital_human" && !item.state?.hidden && Object.keys(item.data_binding ?? {}).length,
));
const variables = computed(() => props.instance.data_binding?.source === "components"
  ? (props.instance.data_binding as unknown as DigitalHumanBinding).variables : []);
const templateError = computed(() => {
  try { parseSpeechTemplate(config.value.speech_template); return ""; }
  catch (reason) { return reason instanceof Error ? reason.message : "话术格式无效"; }
});
const templateDraft = ref(config.value.speech_template);
watch(() => config.value.speech_template, (value) => { templateDraft.value = value; });
const aiOperation = ref<"generate" | "rewrite" | "shorten" | "translate">("rewrite");
const aiTone = ref("专业、简洁");
const aiPreview = ref("");
const aiBaseText = ref("");
const aiApplied = ref(false);
const aiWarnings = ref<string[]>([]);
const aiBusy = ref(false);
const aiError = ref("");
const aiOutboundConfirmed = ref(false);
const providers = ref<DigitalHumanProviderChoice[]>([]);
const ttsProviderId = ref("");
const ttsVoice = ref("");
const ttsTask = ref<SpeechTask | null>(null);
const ttsBusy = ref(false);
const ttsError = ref("");
const ttsPreviewAssetId = ref("");
let ttsController: AbortController | null = null;
watch([templateDraft, aiOperation, aiTone], () => { aiOutboundConfirmed.value = false; });

function update(patch: Record<string, JsonValue>): void {
  if (["audio_asset_id", "speaking_asset_id", "speech_source"].some((key) => key in patch) && !("recording" in patch)) patch.recording = null;
  store.dispatch({ type: "update_props", component_id: props.instance.id, patch });
}

function openLibrary(slot: string, event: Event): void {
  (event.currentTarget as HTMLElement).focus();
  librarySlot.value = slot;
}

function updateTrigger(patch: Partial<DigitalHumanTrigger>): void {
  const trigger = JSON.parse(JSON.stringify({ ...config.value.trigger, ...patch })) as DigitalHumanTrigger;
  if (trigger.kind !== "interval") trigger.interval_seconds = null;
  else trigger.interval_seconds ??= 30;
  if (trigger.kind === "threshold") {
    trigger.threshold ??= 0;
    trigger.variable ??= variables.value[0]?.name ?? "value";
  } else {
    trigger.conditions = [];
    trigger.threshold = null;
  }
  if (trigger.kind === "ranking_change" || trigger.kind === "status_change") {
    trigger.variable ??= variables.value[0]?.name ?? "value";
  }
  if (trigger.kind === "parameter") trigger.parameter ??= store.document?.parameters?.[0]?.name ?? "";
  else trigger.parameter = null;
  update({ trigger: trigger as unknown as JsonValue });
}

type SpeechCondition = NonNullable<DigitalHumanTrigger["conditions"]>[number];
const conditionOperators: Array<{ value: SpeechCondition["operator"]; label: string }> = [
  { value: "gt", label: "大于" }, { value: "gte", label: "大于等于" },
  { value: "lt", label: "小于" }, { value: "lte", label: "小于等于" },
  { value: "eq", label: "等于" }, { value: "neq", label: "不等于" },
  { value: "exists", label: "存在" },
];
function conditionList(): SpeechCondition[] {
  return JSON.parse(JSON.stringify(config.value.trigger.conditions ?? [])) as SpeechCondition[];
}
function addCondition(): void {
  const current = conditionList();
  if (current.length >= 20) return;
  current.push({ variable: variables.value[0]?.name ?? "value", operator: "gt", value: 0 });
  updateTrigger({ conditions: current as unknown as DigitalHumanTrigger["conditions"] });
}
function updateCondition(index: number, patch: Partial<SpeechCondition>): void {
  const current = conditionList();
  const condition = current[index];
  if (!condition) return;
  current[index] = { ...condition, ...patch } as SpeechCondition;
  updateTrigger({ conditions: current as unknown as DigitalHumanTrigger["conditions"] });
}
function removeCondition(index: number): void {
  const current = conditionList();
  current.splice(index, 1);
  updateTrigger({ conditions: current as unknown as DigitalHumanTrigger["conditions"] });
}

function applyTemplate(): void {
  try {
    parseSpeechTemplate(templateDraft.value);
    update({ speech_template: templateDraft.value, speech_segments: [] });
    error.value = "";
  } catch (reason) { error.value = reason instanceof Error ? reason.message : "话术格式无效"; }
}

function segmentList(): SpeechSegment[] {
  return JSON.parse(JSON.stringify(config.value.speech_segments ?? [])) as SpeechSegment[];
}

function updateSegments(next: SpeechSegment[]): void {
  const textLength = next.reduce((total, segment) => total + (segment.text ?? "").length, 0);
  if (textLength > 4000) {
    error.value = "结构化话术文本不能超过 4000 字符。";
    return;
  }
  if (next.length && !next.some((segment) => segment.kind !== "pause")) {
    error.value = "结构化话术至少需要一个文本段。";
    return;
  }
  for (const segment of next) {
    if (segment.kind !== "pause") {
      try { parseSpeechTemplate(segment.text ?? ""); }
      catch (reason) { error.value = reason instanceof Error ? reason.message : "结构化话术格式无效"; return; }
    }
  }
  update({ speech_segments: next as unknown as JsonValue });
  error.value = "";
}

function addSpeechSegment(kind: SpeechSegment["kind"]): void {
  const next = segmentList();
  if (next.length >= 50) return;
  next.push(kind === "pause"
    ? { kind, text: "", duration_ms: 500 }
    : { kind, text: next.length ? (kind === "emphasis" ? "重点：" : "新段落") : config.value.speech_template, duration_ms: 500 });
  updateSegments(next);
}

function updateSpeechSegment(index: number, patch: Partial<SpeechSegment>): void {
  const next = segmentList();
  const current = next[index];
  if (!current) return;
  next[index] = { ...current, ...patch, ...(patch.kind === "pause" ? { text: "" } : {}) } as SpeechSegment;
  updateSegments(next);
}

function removeSpeechSegment(index: number): void {
  const next = segmentList();
  next.splice(index, 1);
  updateSegments(next);
}

function previewResult(): QueryResult | null {
  if (previewMode.value === "current") return currentPreviewResult.value;
  const source = currentPreviewResult.value;
  if (previewMode.value === "threshold" && source?.columns.length && source.rows.length) {
    const result = structuredClone(source);
    const variable = config.value.trigger.variable;
    const mapped = variables.value.find((item) => item.name === variable);
    const index = Math.max(0, result.columns.findIndex((column) => column.name === mapped?.field));
    const existing = result.rows[0]?.[index];
    const threshold = Number(config.value.trigger.threshold ?? 0);
    const simulated = Number.isFinite(threshold)
      ? threshold + (config.value.trigger.direction === "below" ? -1 : 1)
      : 1;
    result.rows[0] = [...(result.rows[0] ?? [])];
    result.rows[0]![index] = typeof existing === "number" || existing === null ? simulated : String(simulated);
    result.request_id = `${result.request_id}:threshold-preview`;
    return result;
  }
  const columns = variables.value.length
    ? variables.value.map((variable) => ({ name: variable.field, data_type: "number" }))
    : [{ name: "value", data_type: "number" }];
  return {
    request_id: "preview:demo",
    columns,
    rows: [columns.map((_column, index) => 72 + index * 8)],
    row_count: 1,
    truncated: false,
    duration_ms: 0,
  };
}

const previewPlan = computed(() => {
  const result = previewResult();
  const states = Object.fromEntries(variables.value.map((variable) => [variable.component_id, {
    status: "success" as const,
    result,
    error: null,
    updatedAt: Date.now(),
  }]));
  return buildSpeechPlan(
    props.instance,
    { result, status: result ? "success" : "idle", error: null },
    states,
  );
});

function stopPreview(): void {
  if (previewUtterance) {
    globalThis.speechSynthesis?.cancel();
    previewUtterance = null;
  }
  previewNotice.value = "试听已停止";
}

function playPreview(): void {
  stopPreview();
  if (!globalThis.speechSynthesis || typeof SpeechSynthesisUtterance === "undefined") {
    previewNotice.value = "当前浏览器不支持语音试听，请检查字幕或预录音频。";
    return;
  }
  const utterance = new SpeechSynthesisUtterance(previewPlan.value.text);
  utterance.lang = config.value.language;
  utterance.rate = config.value.rate;
  utterance.pitch = config.value.pitch;
  utterance.volume = config.value.volume;
  utterance.onend = () => { if (previewUtterance === utterance) previewUtterance = null; };
  utterance.onerror = () => { previewNotice.value = "试听失败，已保留字幕预览。"; };
  previewUtterance = utterance;
  globalThis.speechSynthesis.speak(utterance);
  previewNotice.value = "正在试听当前话术";
}

async function loadTtsProviders(): Promise<void> {
  try {
    const next = await listDigitalHumanProviderDirectory(controller.signal);
    if (controller.signal.aborted) return;
    providers.value = next;
    if (!ttsProviderId.value) {
      ttsProviderId.value = providers.value[0]?.id ?? "";
      ttsVoice.value = providers.value[0]?.default_voice ?? "";
    }
  } catch (reason) {
    if (!controller.signal.aborted) ttsError.value = reason instanceof ApiError ? reason.message : "TTS 供应商列表加载失败";
  }
}

function selectTtsProvider(id: string): void {
  ttsProviderId.value = id;
  ttsVoice.value = providers.value.find((provider) => provider.id === id)?.default_voice ?? "";
  ttsPreviewAssetId.value = "";
  ttsTask.value = null;
}

function wait(milliseconds: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(resolve, milliseconds);
    signal.addEventListener("abort", () => {
      window.clearTimeout(timer);
      reject(new DOMException("The TTS preview was cancelled.", "AbortError"));
    }, { once: true });
  });
}

async function generateTtsPreview(): Promise<void> {
  if (ttsBusy.value) return;
  const screenId = store.screen?.id;
  if (!screenId || !ttsProviderId.value || !ttsVoice.value.trim()) {
    ttsError.value = "请先选择已配置的 TTS 供应商和声音。";
    return;
  }
  ttsController?.abort();
  const nextController = new AbortController();
  ttsController = nextController;
  ttsBusy.value = true;
  ttsError.value = "";
  ttsTask.value = null;
  ttsPreviewAssetId.value = "";
  try {
    const plan = await createDigitalHumanSpeechPlan({
      screen_id: screenId,
      component_id: props.instance.id,
      text: previewPlan.value.text,
      language: config.value.language,
      provider_id: ttsProviderId.value,
      voice: ttsVoice.value.trim(),
      rate: config.value.rate,
      pitch: config.value.pitch,
      volume: config.value.volume,
      data_fingerprint: JSON.stringify({ values: [...previewPlan.value.values], segments: config.value.speech_segments }).slice(0, 128),
    }, nextController.signal);
    let task = await queueDigitalHumanSpeechTask(plan.id, nextController.signal);
    ttsTask.value = task;
    const deadline = Date.now() + 60_000;
    while ((task.status === "queued" || task.status === "running") && Date.now() < deadline) {
      await wait(500, nextController.signal);
      task = await getDigitalHumanSpeechTask(task.id, nextController.signal);
      ttsTask.value = task;
    }
    if (task.status !== "succeeded" || !task.asset_id) {
      ttsError.value = task.error_code || (task.status === "queued" || task.status === "running" ? "TTS 生成超时" : "TTS 生成失败");
      return;
    }
    ttsPreviewAssetId.value = task.asset_id;
    previewNotice.value = "TTS 试听音频已生成；确认采用后才会写入草稿。";
  } catch (reason) {
    if (!(reason instanceof DOMException && reason.name === "AbortError")) {
      ttsError.value = reason instanceof ApiError ? `${reason.message} (${reason.code})` : "TTS 生成失败，已保留字幕预览。";
    }
  } finally {
    if (ttsController === nextController) {
      ttsBusy.value = false;
      ttsController = null;
    }
  }
}

async function applyTtsPreview(): Promise<void> {
  if (!ttsPreviewAssetId.value) return;
  try {
    const asset = assets.value.find((item) => item.id === ttsPreviewAssetId.value)
      ?? await getAsset(ttsPreviewAssetId.value, controller.signal);
    const duration = asset.media?.duration_seconds;
    if (!duration || duration <= 0) {
      ttsError.value = "TTS 资产缺少有效时长，无法采用。";
      return;
    }
    update({
      audio_asset_id: ttsPreviewAssetId.value,
      speech_source: "audio",
      recording: {
        asset_id: asset.id,
        sha256: asset.sha256,
        transcript: previewPlan.value.text,
        duration_seconds: duration,
      } as unknown as JsonValue,
    });
    await refreshAssets();
    previewNotice.value = "TTS 音频已采用到草稿，发布后才会在线使用。";
  } catch (reason) {
    if (!controller.signal.aborted) ttsError.value = reason instanceof ApiError ? `${reason.message} (${reason.code})` : "TTS 资产信息读取失败。";
  }
}

async function clearSpeechCache(): Promise<void> {
  try {
    await apiRequest("/api/admin/digital-human/cache/clear", { method: "POST" });
    previewNotice.value = "未引用语音缓存已清理";
  } catch (reason) {
    previewNotice.value = reason instanceof ApiError ? `${reason.message} (${reason.code})` : "缓存清理失败";
  }
}

async function generateAiPreview(): Promise<void> {
  if (aiBusy.value) return;
  if (!aiOutboundConfirmed.value) {
    aiError.value = "请先确认将当前话术和允许变量发送到 AI 供应商。";
    return;
  }
  aiBusy.value = true;
  aiError.value = "";
  try {
    const result = await apiRequest<{ text: string; warnings: string[]; preview_only: true }>(
      "/api/admin/digital-human/ai/draft",
      {
        method: "POST",
        json: {
          operation: aiOperation.value,
          source_text: templateDraft.value,
          language: config.value.language,
          tone: aiTone.value,
          allowed_variables: variables.value.map((variable) => variable.name),
        },
      },
    );
    aiBaseText.value = templateDraft.value;
    aiPreview.value = result.text;
    aiApplied.value = false;
    aiWarnings.value = result.warnings;
  } catch (reason) {
    aiError.value = reason instanceof ApiError ? `${reason.message} (${reason.code})` : "AI 预览暂时不可用";
  } finally {
    aiBusy.value = false;
  }
}

function applyAiPreview(): void {
  if (!aiPreview.value) return;
  templateDraft.value = aiPreview.value;
  applyTemplate();
  aiApplied.value = true;
}

function undoAiPreview(): void {
  if (!aiApplied.value || !aiBaseText.value) return;
  templateDraft.value = aiBaseText.value;
  applyTemplate();
  aiApplied.value = false;
}

async function loadFields(): Promise<void> {
  fieldController?.abort();
  const nextController = new AbortController();
  fieldController = nextController;
  fieldNames.value = [];
  field.value = "";
  const component = sources.value.find((item) => item.id === componentId.value);
  if (!component || !store.document) return;
  fieldLoading.value = true;
  try {
    const local = resolveLocalResult(component, component.data_binding ?? {});
    const result = local ?? await queryScreenDocument(
      JSON.parse(JSON.stringify(store.document)), component.id,
      Object.fromEntries((store.document.parameters ?? []).map((parameter) => [parameter.name, parameter.default ?? null])),
      nextController.signal,
    );
    if (!nextController.signal.aborted && fieldController === nextController) {
      fieldNames.value = result.columns.map((column) => column.name).filter((name) => !sensitiveSpeechField(name));
      currentPreviewResult.value = result;
      field.value = fieldNames.value[0] ?? "";
    }
  } catch {
    if (!nextController.signal.aborted) error.value = "字段加载失败";
  } finally {
    if (fieldController === nextController) fieldLoading.value = false;
  }
}

function saveVariables(next: Array<DigitalHumanBinding["variables"][number]>): void {
  store.dispatch({
    type: "update_data_binding", component_id: props.instance.id,
    data_binding: next.length ? { source: "components", variables: next as unknown as JsonValue } : {},
  });
}

function addVariable(): void {
  const name = variableName.value.trim();
  try { parseSpeechTemplate("{{" + name + "}}"); }
  catch { error.value = "变量名称无效"; return; }
  if (!componentId.value || !fieldNames.value.includes(field.value) || variables.value.some((variable) => variable.name === name)) {
    error.value = "请选择字段并使用唯一的变量名称";
    return;
  }
  saveVariables([...variables.value, { name, component_id: componentId.value, field: field.value, row: 0 }]);
  variableName.value = "value" + (variables.value.length + 1);
  error.value = "";
}

function demo(): void {
  store.dispatch({ type: "update_data_binding", component_id: props.instance.id, data_binding: createMockBinding("builtin.digital_human") });
}

async function refreshAssets(): Promise<void> {
  try {
    const items = await listAssets({ limit: 100 }, controller.signal);
    for (const key of ["avatar_asset_id", "speaking_asset_id", "audio_asset_id"]) {
      const id = props.instance.props?.[key];
      if (typeof id === "string" && id && !items.some((asset) => asset.id === id)) {
        try { items.push(await getAsset(id, controller.signal)); }
        catch (reason) { if (!(reason instanceof ApiError && reason.status === 404)) throw reason; }
      }
    }
    if (!controller.signal.aborted) assets.value = items;
  }
  catch { if (!controller.signal.aborted) error.value = "资源列表加载失败"; }
}

async function upload(event: Event, key: string): Promise<void> {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  const targetId = props.instance.id;
  pending.value = true;
  try {
    const asset = await uploadAsset(file, undefined, controller.signal);
    if (controller.signal.aborted || props.instance.id !== targetId) return;
    update({
      [key]: asset.id,
      ...(key === "avatar_asset_id" ? { avatar_kind: asset.asset_type === "video" ? "video" : "image" } : {}),
      ...(key === "speaking_asset_id" ? { speaking_kind: asset.asset_type === "video" ? "video" : "image" } : {}),
    });
    await refreshAssets();
  } catch (reason) { if (!controller.signal.aborted) error.value = reason instanceof ApiError ? `${reason.message} (${reason.code})` : "资源上传失败，请检查文件格式与大小"; }
  finally { pending.value = false; input.value = ""; }
}

function selectLibraryAsset(asset: ScreenAsset): void {
  const key = librarySlot.value;
  if (key === "mapped") {
    mappingAsset.value = asset;
    mappingRecording.value = config.value.recordings.find((item) => item.asset_id === asset.id) ?? null;
    librarySlot.value = null;
    return;
  }
  if (!key || key === "manage") return;
  assets.value = [asset, ...assets.value.filter((item) => item.id !== asset.id)];
  update({
    [key]: asset.id,
    ...(key === "avatar_asset_id" ? { avatar_kind: asset.asset_type === "video" ? "video" : "image" } : {}),
    ...(key === "speaking_asset_id" ? { speaking_kind: asset.asset_type === "video" ? "video" : "image" } : {}),
  });
  librarySlot.value = null;
}

function confirmMappedRecording(recording: Recording | null): void {
  if (!mappingAsset.value) return;
  const current = [...(config.value.recordings ?? [])] as Recording[];
  const index = current.findIndex((item) => item.asset_id === mappingAsset.value!.id);
  if (!recording) {
    if (index >= 0) current.splice(index, 1);
  } else {
    const next = {
      ...recording,
      priority: index >= 0 ? current[index]!.priority ?? 0 : 0,
      conditions: index >= 0 ? current[index]!.conditions ?? [] : [],
      condition_mode: index >= 0 ? current[index]!.condition_mode ?? "all" : "all",
    } as Recording;
    if (index >= 0) current[index] = next;
    else current.push(next);
    mappingRecording.value = next;
  }
  update({ recordings: current as unknown as JsonValue });
  if (!recording) { mappingAsset.value = null; mappingRecording.value = null; }
}

function updateMappedRecording(index: number, patch: Partial<Recording>): void {
  const current = JSON.parse(JSON.stringify(config.value.recordings ?? [])) as Recording[];
  const recording = current[index];
  if (!recording) return;
  current[index] = { ...recording, ...patch };
  update({ recordings: current as unknown as JsonValue });
  if (mappingAsset.value?.id === recording.asset_id) mappingRecording.value = current[index]!;
}

function updateMappedConditions(index: number, patch: Partial<RecordingCondition>): void {
  const current = [...(config.value.recordings ?? [])] as Recording[];
  const recording = current[index];
  if (!recording) return;
  const conditions = [...(recording.conditions ?? [])] as RecordingCondition[];
  conditions[0] = { ...(conditions[0] ?? { variable: variables.value[0]?.name ?? "value", operator: "gt", value: 0 }), ...patch } as RecordingCondition;
  updateMappedRecording(index, { conditions: conditions as unknown as Recording["conditions"] });
}

function removeMappedRecording(index: number): void {
  const current = [...(config.value.recordings ?? [])] as Recording[];
  const [removed] = current.splice(index, 1);
  update({ recordings: current as unknown as JsonValue });
  if (removed && mappingAsset.value?.id === removed.asset_id) { mappingAsset.value = null; mappingRecording.value = null; }
}

function addAction(): void {
  const asset = assets.value.find((item) => item.asset_type === "image" || item.asset_type === "video");
  if (!asset || (config.value.actions?.length ?? 0) >= 8) return;
  const action: Action = {
    id: `action-${Date.now()}`,
    kind: "emphasis",
    asset_id: asset.id,
    asset_kind: asset.asset_type === "video" ? "video" : "image",
    priority: 0,
    duration_ms: 1200,
    conditions: [],
    condition_mode: "all",
  };
  update({ actions: [...(config.value.actions ?? []), action] as unknown as JsonValue });
}

function updateAction(index: number, patch: Partial<Action>): void {
  const actions = [...(config.value.actions ?? [])] as Action[];
  const action = actions[index];
  if (!action) return;
  actions[index] = { ...action, ...patch };
  update({ actions: actions as unknown as JsonValue });
}

function removeAction(index: number): void {
  const actions = [...(config.value.actions ?? [])] as Action[];
  actions.splice(index, 1);
  update({ actions: actions as unknown as JsonValue });
}

function updateActionCondition(index: number, patch: Partial<ActionCondition>): void {
  const actions = [...(config.value.actions ?? [])] as Action[];
  const action = actions[index];
  if (!action) return;
  const condition = action.conditions?.[0] ?? {
    variable: variables.value[0]?.name ?? "value",
    operator: "gt" as const,
    value: 0,
  };
  actions[index] = {
    ...action,
    conditions: [{ ...condition, ...patch }] as Action["conditions"],
  };
  update({ actions: actions as unknown as JsonValue });
}

function clearActionCondition(index: number): void {
  updateAction(index, { conditions: [] });
}

function selectAsset(key: string, event: Event): void {
  const id = (event.target as HTMLSelectElement).value;
  const asset = assets.value.find((item) => item.id === id);
  update({
    [key]: id,
    ...(key === "avatar_asset_id" ? { avatar_kind: asset?.asset_type === "video" ? "video" : "image" } : {}),
    ...(key === "speaking_asset_id" ? { speaking_kind: asset?.asset_type === "video" ? "video" : "image" } : {}),
  });
}
const assetSlots = [
  { key: "avatar_asset_id", label: "待机形象", accept: "image/png,image/jpeg,image/webp,video/mp4,video/webm", types: ["image", "video"] },
  { key: "speaking_asset_id", label: "播报形象", accept: "image/png,image/jpeg,image/webp,video/mp4,video/webm", types: ["image", "video"] },
  { key: "audio_asset_id", label: "预录音频", accept: "audio/mpeg,audio/wav,audio/ogg", types: ["audio"] },
];
onMounted(refreshAssets);
onMounted(() => void loadTtsProviders());
onBeforeUnmount(() => { controller.abort(); fieldController?.abort(); ttsController?.abort(); stopPreview(); });
</script>

<template>
  <div class="speech-inspector">
    <button type="button" @click="openLibrary('manage', $event)"><FolderOpen :size="16" />资源库</button>
    <AssetLibraryDialog v-if="librarySlot" :selected-id="typeof instance.props?.[librarySlot] === 'string' ? instance.props[librarySlot] as string : ''" :allowed-types="libraryTypes" :in-use-ids="inUseIds" :selectable="librarySlot !== 'manage'" @close="librarySlot = null" @select="selectLibraryAsset" @changed="refreshAssets()" />
    <p v-if="error || templateError" role="alert">{{ error || templateError }}</p>
    <details open>
      <summary>外观</summary>
      <label>名称<input :value="config.name" maxlength="120" @change="update({ name: ($event.target as HTMLInputElement).value })" /></label>
      <label>身份<input :value="config.role" maxlength="120" @change="update({ role: ($event.target as HTMLInputElement).value })" /></label>
      <div v-for="slot in assetSlots.filter((item) => item.key !== 'audio_asset_id')" :key="slot.key" class="speech-inspector__asset">
        <label>{{ slot.label }}
          <select :value="config[slot.key as keyof typeof config]" @change="selectAsset(slot.key, $event)">
            <option value="">默认形象</option>
            <option v-for="asset in assets.filter((item) => slot.types.includes(item.asset_type))" :key="asset.id" :value="asset.id">{{ asset.name }} · v{{ asset.version }}</option>
          </select>
        </label>
        <button type="button" :title="'选择' + slot.label" :aria-label="'选择' + slot.label" @click="openLibrary(slot.key, $event)"><FolderOpen :size="16" /></button>
        <label class="speech-inspector__upload" :title="'上传' + slot.label"><Upload :size="16" /><input type="file" :accept="slot.accept" :aria-label="'上传' + slot.label" :disabled="pending" @change="upload($event, slot.key)" /></label>
      </div>
      <label>画面适配<select :value="config.fit" @change="update({ fit: ($event.target as HTMLSelectElement).value })"><option value="contain">完整显示</option><option value="cover">裁剪填充</option><option value="none">原始比例</option></select></label>
      <label class="check"><input type="checkbox" :checked="config.mirror" @change="update({ mirror: ($event.target as HTMLInputElement).checked })" />镜像</label>
      <label class="check"><input type="checkbox" :checked="config.show_identity" @change="update({ show_identity: ($event.target as HTMLInputElement).checked })" />显示身份</label>
      <label class="check"><input type="checkbox" :checked="config.show_status" @change="update({ show_status: ($event.target as HTMLInputElement).checked })" />显示状态</label>
      <label class="check"><input type="checkbox" :checked="config.animation" @change="update({ animation: ($event.target as HTMLInputElement).checked })" />说话动画</label>
      <div class="speech-inspector__mapping-heading"><strong>动作预设</strong><button type="button" :disabled="!assets.some((asset) => asset.asset_type === 'image' || asset.asset_type === 'video')" @click="addAction"><Plus :size="14" />添加动作</button></div>
      <div v-for="(action, index) in config.actions" :key="action.id" class="speech-inspector__mapping">
        <div class="speech-inspector__mapping-title"><span>{{ action.id }}</span><button type="button" title="移除动作" aria-label="移除动作" @click="removeAction(index)"><Trash2 :size="13" /></button></div>
        <label>资源<select :value="action.asset_id" @change="updateAction(index, { asset_id: ($event.target as HTMLSelectElement).value, asset_kind: assets.find((asset) => asset.id === ($event.target as HTMLSelectElement).value)?.asset_type === 'video' ? 'video' : 'image' })"><option v-for="asset in assets.filter((item) => item.asset_type === 'image' || item.asset_type === 'video')" :key="asset.id" :value="asset.id">{{ asset.name }} · v{{ asset.version }}</option></select></label>
        <label>动作<select :value="action.kind" @change="updateAction(index, { kind: ($event.target as HTMLSelectElement).value as Action['kind'] })"><option value="nod">点头</option><option value="wave">挥手</option><option value="emphasis">强调</option></select></label>
        <label>时长（毫秒）<input type="number" min="100" max="10000" step="100" :value="action.duration_ms" @change="updateAction(index, { duration_ms: Number(($event.target as HTMLInputElement).value) })" /></label>
        <label>优先级<input type="number" min="-100" max="100" :value="action.priority ?? 0" @change="updateAction(index, { priority: Number(($event.target as HTMLInputElement).value) })" /></label>
        <label>条件方式<select :value="action.condition_mode ?? 'all'" @change="updateAction(index, { condition_mode: ($event.target as HTMLSelectElement).value as 'all' | 'any' })"><option value="all">全部满足</option><option value="any">任一满足</option></select></label>
        <div v-if="action.conditions?.[0]" class="speech-inspector__condition">
          <select :value="action.conditions[0].variable" aria-label="动作条件变量" @change="updateActionCondition(index, { variable: ($event.target as HTMLSelectElement).value })"><option value="value">value</option><option v-for="variable in variables" :key="variable.name" :value="variable.name">{{ variable.name }}</option></select>
          <select :value="action.conditions[0].operator" aria-label="动作条件运算符" @change="updateActionCondition(index, { operator: ($event.target as HTMLSelectElement).value as ActionCondition['operator'], value: ($event.target as HTMLSelectElement).value === 'exists' ? null : action.conditions[0].value ?? 0 })"><option v-for="operator in conditionOperators" :key="operator.value" :value="operator.value">{{ operator.label }}</option></select>
          <input v-if="action.conditions[0].operator !== 'exists'" :value="String(action.conditions[0].value ?? '')" aria-label="动作条件值" @change="updateActionCondition(index, { value: ($event.target as HTMLInputElement).value })" />
          <button type="button" title="清除动作条件" aria-label="清除动作条件" @click="clearActionCondition(index)"><Trash2 :size="13" /></button>
        </div>
        <button v-else type="button" @click="updateActionCondition(index, {})">增加动作条件</button>
      </div>
    </details>
    <details open>
      <summary>数据与话术</summary>
      <div class="speech-inspector__actions"><button type="button" @click="demo">演示数据</button><button type="button" @click="saveVariables([])">静态话术</button></div>
      <label>数据组件<select v-model="componentId" @change="loadFields"><option value="">请选择</option><option v-for="source in sources" :key="source.id" :value="source.id">{{ source.props?.title || source.props?.label || source.type }} · {{ source.id.slice(0, 8) }}</option></select></label>
      <label>字段<select v-model="field" :disabled="fieldLoading"><option value="">{{ fieldLoading ? "加载中" : "请选择" }}</option><option v-for="name in fieldNames" :key="name">{{ name }}</option></select></label>
      <div class="speech-inspector__actions"><label>变量名称<input v-model="variableName" maxlength="128" /></label><button type="button" title="添加变量" aria-label="添加变量" @click="addVariable"><Plus :size="16" /></button></div>
      <div v-for="(variable, index) in variables" :key="variable.name" class="speech-inspector__variable">
        <button type="button" :title="'插入 ' + variable.name" @click="templateDraft += '{{' + variable.name + '}}'">{{ variable.name }}</button>
        <span>{{ variable.field }}</span>
        <button type="button" title="移除变量" aria-label="移除变量" @click="saveVariables(variables.filter((_, position) => position !== index))"><Trash2 :size="14" /></button>
      </div>
      <label>话术模板<textarea v-model="templateDraft" rows="5" maxlength="4000" spellcheck="false" /></label>
      <button type="button" @click="applyTemplate">应用话术</button>
      <div class="speech-inspector__script" aria-label="结构化话术">
        <div class="speech-inspector__mapping-heading"><strong>结构化话术</strong><span>段落、停顿和强调</span></div>
        <div class="speech-inspector__actions">
          <button type="button" @click="addSpeechSegment('paragraph')"><Plus :size="13" />段落</button>
          <button type="button" @click="addSpeechSegment('pause')"><Plus :size="13" />停顿</button>
          <button type="button" @click="addSpeechSegment('emphasis')"><Plus :size="13" />强调</button>
          <button v-if="config.speech_segments.length" type="button" @click="update({ speech_segments: [] })">使用模板</button>
        </div>
        <div v-for="(segment, index) in config.speech_segments" :key="index" class="speech-inspector__script-row">
          <select :value="segment.kind" :aria-label="`话术段落类型 ${index + 1}`" @change="updateSpeechSegment(index, { kind: ($event.target as HTMLSelectElement).value as SpeechSegment['kind'] })">
            <option value="paragraph">段落</option><option value="pause">停顿</option><option value="emphasis">强调</option>
          </select>
          <textarea v-if="segment.kind !== 'pause'" :value="segment.text" rows="2" maxlength="4000" :aria-label="`话术段落文本 ${index + 1}`" @change="updateSpeechSegment(index, { text: ($event.target as HTMLTextAreaElement).value })" />
          <label v-else>时长（毫秒）<input type="number" min="100" max="10000" step="100" :value="segment.duration_ms" :aria-label="`停顿时长 ${index + 1}`" @change="updateSpeechSegment(index, { duration_ms: Number(($event.target as HTMLInputElement).value) })" /></label>
          <button type="button" title="移除话术段落" :aria-label="`移除话术段落 ${index + 1}`" @click="removeSpeechSegment(index)"><Trash2 :size="13" /></button>
        </div>
      </div>
      <div class="speech-inspector__preview" aria-labelledby="speech-preview-title">
        <div class="speech-inspector__preview-heading"><strong id="speech-preview-title">话术预览</strong><span :data-preview-mode="previewMode">{{ previewMode === "demo" ? "演示数据" : previewMode === "current" ? "当前查询" : "阈值模拟" }}</span></div>
        <label>预览数据<select v-model="previewMode" data-preview-data><option value="demo">使用演示数据</option><option value="current">使用当前查询结果</option><option value="threshold">模拟阈值变化</option></select></label>
        <p class="speech-inspector__preview-text" data-preview-text>{{ previewPlan.text }}</p>
        <p v-if="previewPlan.code" class="speech-inspector__ai-error" role="alert">{{ previewPlan.code }}</p>
        <div class="speech-inspector__actions">
          <button type="button" @click="playPreview">试听当前话术</button>
          <button type="button" @click="stopPreview">停止试听</button>
          <button type="button" @click="clearSpeechCache">清空未引用缓存</button>
        </div>
        <p v-if="previewNotice" class="speech-inspector__ai-context" role="status">{{ previewNotice }}</p>
        <div class="speech-inspector__tts" aria-labelledby="speech-tts-title">
          <strong id="speech-tts-title">TTS 供应商试听</strong>
          <label>供应商<select :value="ttsProviderId" :disabled="ttsBusy || !providers.length" @change="selectTtsProvider(($event.target as HTMLSelectElement).value)">
            <option value="">{{ providers.length ? "请选择已配置供应商" : "暂无已配置供应商" }}</option>
            <option v-for="provider in providers" :key="provider.id" :value="provider.id">{{ provider.name }} · {{ provider.language }}</option>
          </select></label>
          <label>声音<input v-model="ttsVoice" maxlength="120" :disabled="ttsBusy || !ttsProviderId" placeholder="供应商默认声音" /></label>
          <button type="button" :disabled="ttsBusy || !ttsProviderId || !ttsVoice.trim()" @click="generateTtsPreview"><Volume2 :size="14" />{{ ttsBusy ? "生成中…" : "生成 TTS 试听" }}</button>
          <p v-if="ttsTask" class="speech-inspector__ai-context" role="status">任务：{{ ttsTask.status }}{{ ttsTask.error_code ? ` · ${ttsTask.error_code}` : "" }}</p>
          <p v-if="ttsError" class="speech-inspector__ai-error" role="alert">{{ ttsError }}</p>
          <audio v-if="ttsPreviewAssetId" :src="assetUrl(ttsPreviewAssetId)" controls preload="metadata" aria-label="TTS 试听音频" />
          <button v-if="ttsPreviewAssetId" type="button" @click="applyTtsPreview">采用此音频到草稿</button>
        </div>
      </div>
      <details class="speech-inspector__ai">
        <summary><Sparkles :size="14" aria-hidden="true" />AI 话术预览</summary>
        <label>操作<select v-model="aiOperation"><option value="generate">生成</option><option value="rewrite">改写</option><option value="shorten">缩短</option><option value="translate">翻译</option></select></label>
        <label>语气<input v-model="aiTone" maxlength="120" /></label>
        <p class="speech-inspector__ai-context">仅发送当前话术和已绑定变量：{{ variables.map((variable) => variable.name).join("、") || "无" }}</p>
        <label class="check speech-inspector__ai-consent"><input v-model="aiOutboundConfirmed" type="checkbox" />我确认以上内容可以发送给已配置的 AI 供应商</label>
        <button type="button" :disabled="aiBusy || !aiOutboundConfirmed" @click="generateAiPreview"><Sparkles :size="14" aria-hidden="true" />{{ aiBusy ? "生成中…" : "生成预览" }}</button>
        <p v-if="aiError" class="speech-inspector__ai-error" role="alert">{{ aiError }}</p>
        <div v-if="aiPreview" class="speech-inspector__ai-result">
          <div class="speech-inspector__ai-diff" aria-label="AI 话术差异">
            <div><span>原文</span><del>{{ aiBaseText }}</del></div>
            <div><span>预览</span><ins>{{ aiPreview }}</ins></div>
          </div>
          <ul v-if="aiWarnings.length"><li v-for="warning in aiWarnings" :key="warning">{{ warning }}</li></ul>
          <div class="speech-inspector__ai-actions"><button type="button" :disabled="aiApplied" @click="applyAiPreview">应用预览到草稿</button><button v-if="aiApplied" type="button" @click="undoAiPreview">撤销应用</button></div>
        </div>
      </details>
      <label>空值文案<input :value="config.empty_text" maxlength="500" @change="update({ empty_text: ($event.target as HTMLInputElement).value })" /></label>
      <label>错误文案<input :value="config.error_text" maxlength="500" @change="update({ error_text: ($event.target as HTMLInputElement).value })" /></label>
    </details>
    <details @toggle="soundOpen = ($event.target as HTMLDetailsElement).open">
      <summary>声音</summary>
      <label class="check"><input type="checkbox" :checked="config.voice_enabled" @change="update({ voice_enabled: ($event.target as HTMLInputElement).checked })" />启用声音</label>
      <label class="check"><input type="checkbox" :checked="config.muted" @change="update({ muted: ($event.target as HTMLInputElement).checked })" />默认静音</label>
      <label>播报来源<select :value="config.speech_source" @change="update({ speech_source: ($event.target as HTMLSelectElement).value })"><option value="auto">音频优先</option><option value="browser">浏览器语音</option><option value="audio">预录音频</option><option value="video">播报视频原声</option></select></label>
      <label>音频<select :value="config.audio_asset_id" @change="selectAsset('audio_asset_id', $event)"><option value="">浏览器语音</option><option v-for="asset in assets.filter((item) => item.asset_type === 'audio')" :key="asset.id" :value="asset.id">{{ asset.name }} · v{{ asset.version }}</option></select></label>
      <button type="button" @click="openLibrary('audio_asset_id', $event)"><FolderOpen :size="16" />选择预录音频</button>
      <label class="speech-inspector__upload" title="上传音频"><Upload :size="16" /><input type="file" accept="audio/mpeg,audio/wav,audio/ogg" aria-label="上传音频" :disabled="pending" @change="upload($event, 'audio_asset_id')" /></label>
      <SpeechRecordingEditor v-if="soundOpen && recordingAsset" :key="recordingAsset.id" :media="recordingAsset" :recording="config.recording" :in-use-ids="inUseIds" @confirm="update({ recording: $event as unknown as JsonValue })" />
      <label>语言<select :value="config.language" @change="update({ language: ($event.target as HTMLSelectElement).value })"><option value="zh-CN">普通话</option><option value="en-US">英语</option></select></label>
      <label>语速<input type="range" min="0.5" max="2" step="0.1" :value="config.rate" @change="update({ rate: Number(($event.target as HTMLInputElement).value) })" /></label>
      <label>音调<input type="range" min="0" max="2" step="0.1" :value="config.pitch" @change="update({ pitch: Number(($event.target as HTMLInputElement).value) })" /></label>
      <label>音量<input type="range" min="0" max="1" step="0.05" :value="config.volume" @change="update({ volume: Number(($event.target as HTMLInputElement).value) })" /></label>
      <div class="speech-inspector__mapping-heading"><strong>条件片段</strong><button type="button" @click="openLibrary('mapped', $event)"><FolderOpen :size="14" />添加片段</button></div>
      <div v-for="(recording, index) in config.recordings" :key="recording.asset_id" class="speech-inspector__mapping">
        <div class="speech-inspector__mapping-title"><span>{{ assets.find((asset) => asset.id === recording.asset_id)?.name || recording.asset_id }}</span><button type="button" title="编辑片段" @click="mappingAsset = assets.find((asset) => asset.id === recording.asset_id) ?? null; mappingRecording = recording"><Pencil :size="13" /></button><button type="button" title="移除片段" aria-label="移除条件片段" @click="removeMappedRecording(index)"><Trash2 :size="13" /></button></div>
        <label>匹配方式<select :value="recording.condition_mode ?? 'all'" @change="updateMappedRecording(index, { condition_mode: ($event.target as HTMLSelectElement).value as 'all' | 'any' })"><option value="all">全部条件</option><option value="any">任一条件</option></select></label>
        <label>优先级<input type="number" min="-100" max="100" :value="recording.priority ?? 0" @change="updateMappedRecording(index, { priority: Number(($event.target as HTMLInputElement).value) })" /></label>
        <div v-if="recording.conditions?.[0]" class="speech-inspector__condition">
          <select :value="recording.conditions[0].variable" aria-label="片段条件变量" @change="updateMappedConditions(index, { variable: ($event.target as HTMLSelectElement).value })"><option value="value">value</option><option v-for="variable in variables" :key="variable.name" :value="variable.name">{{ variable.name }}</option></select>
          <select :value="recording.conditions[0].operator" aria-label="片段条件运算符" @change="updateMappedConditions(index, { operator: ($event.target as HTMLSelectElement).value as RecordingCondition['operator'] })"><option v-for="operator in conditionOperators" :key="operator.value" :value="operator.value">{{ operator.label }}</option></select>
          <input v-if="recording.conditions[0].operator !== 'exists'" :value="String(recording.conditions[0].value ?? '')" aria-label="片段条件值" @change="updateMappedConditions(index, { value: ($event.target as HTMLInputElement).value })" />
        </div>
      </div>
      <SpeechRecordingEditor v-if="mappingAsset" :key="mappingAsset.id" :media="mappingAsset" :recording="mappingRecording" :in-use-ids="inUseIds" @confirm="confirmMappedRecording" />
    </details>
    <details>
      <summary>触发</summary>
      <label class="check"><input type="checkbox" :checked="config.auto_play" @change="update({ auto_play: ($event.target as HTMLInputElement).checked })" />自动播报</label>
      <label>触发方式<select :value="config.trigger.kind" @change="updateTrigger({ kind: ($event.target as HTMLSelectElement).value as DigitalHumanTrigger['kind'] })">
        <option value="initial">首次加载</option><option value="manual">手动</option><option value="interval">定时</option><option value="data_change">数据变化</option><option value="ranking_change">排名变化</option><option value="status_change">状态变化</option><option value="threshold">阈值变化</option><option value="parameter">参数变化</option>
      </select></label>
      <label v-if="config.trigger.kind === 'interval'">间隔（秒）<input type="number" min="10" max="86400" :value="config.trigger.interval_seconds" @change="updateTrigger({ interval_seconds: Number(($event.target as HTMLInputElement).value) })" /></label>
      <template v-if="config.trigger.kind === 'threshold'">
        <div class="speech-inspector__condition-heading"><span>条件组</span><button type="button" @click="addCondition">增加条件</button></div>
        <label v-if="config.trigger.conditions?.length">匹配方式<select :value="config.trigger.condition_mode" @change="updateTrigger({ condition_mode: ($event.target as HTMLSelectElement).value as 'all' | 'any' })"><option value="all">全部满足</option><option value="any">任一满足</option></select></label>
        <div v-for="(condition, index) in config.trigger.conditions" :key="index" class="speech-inspector__condition">
          <select :value="condition.variable" aria-label="条件变量" @change="updateCondition(index, { variable: ($event.target as HTMLSelectElement).value })"><option value="value">value</option><option v-for="variable in variables" :key="variable.name" :value="variable.name">{{ variable.name }}</option></select>
          <select :value="condition.operator" aria-label="条件运算符" @change="updateCondition(index, { operator: ($event.target as HTMLSelectElement).value as SpeechCondition['operator'], value: ($event.target as HTMLSelectElement).value === 'exists' ? null : condition.value ?? 0 })"><option v-for="operator in conditionOperators" :key="operator.value" :value="operator.value">{{ operator.label }}</option></select>
          <input v-if="condition.operator !== 'exists'" :value="String(condition.value ?? '')" aria-label="条件值" @change="updateCondition(index, { value: ($event.target as HTMLInputElement).value })" />
          <button type="button" title="移除条件" aria-label="移除条件" @click="removeCondition(index)"><Trash2 :size="14" /></button>
        </div>
        <label v-if="config.trigger.conditions?.length">条件优先级<input type="number" min="-100" max="100" :value="config.trigger.priority" @change="updateTrigger({ priority: Number(($event.target as HTMLInputElement).value) })" /></label>
        <label v-if="config.trigger.conditions?.length">条件防抖（秒）<input type="number" min="0" max="3600" :value="config.trigger.debounce_seconds" @change="updateTrigger({ debounce_seconds: Number(($event.target as HTMLInputElement).value) })" /></label>
        <label>阈值变量<select :value="config.trigger.variable" @change="updateTrigger({ variable: ($event.target as HTMLSelectElement).value })"><option value="value">value</option><option v-for="variable in variables" :key="variable.name" :value="variable.name">{{ variable.name }}</option></select></label>
        <label>阈值<input type="number" :value="config.trigger.threshold" @change="updateTrigger({ threshold: Number(($event.target as HTMLInputElement).value) })" /></label>
        <label>方向<select :value="config.trigger.direction" @change="updateTrigger({ direction: ($event.target as HTMLSelectElement).value as 'above' | 'below' })"><option value="above">高于</option><option value="below">低于</option></select></label>
        <label>播报时机<select :value="config.trigger.edge" @change="updateTrigger({ edge: ($event.target as HTMLSelectElement).value as 'enter' | 'recover' | 'both' })"><option value="enter">进入异常</option><option value="recover">恢复正常</option><option value="both">进入和恢复</option></select></label>
      </template>
      <label v-if="config.trigger.kind === 'ranking_change' || config.trigger.kind === 'status_change'">变化变量<select :value="config.trigger.variable" @change="updateTrigger({ variable: ($event.target as HTMLSelectElement).value })"><option value="value">value</option><option v-for="variable in variables" :key="variable.name" :value="variable.name">{{ variable.name }}</option></select></label>
      <label v-if="config.trigger.kind === 'parameter'">参数<select :value="config.trigger.parameter" @change="updateTrigger({ parameter: ($event.target as HTMLSelectElement).value })"><option v-for="parameter in store.document?.parameters" :key="parameter.name">{{ parameter.name }}</option></select></label>
      <label>冷却（秒）<input type="number" min="1" max="86400" :value="config.trigger.cooldown_seconds" @change="updateTrigger({ cooldown_seconds: Number(($event.target as HTMLInputElement).value) })" /></label>
      <label>最小变化量<input type="number" min="0" :value="config.trigger.min_change" @change="updateTrigger({ min_change: Number(($event.target as HTMLInputElement).value) })" /></label>
      <div class="speech-inspector__quiet-heading"><strong>规则有效时段</strong><span>按组件时区执行</span></div>
      <div class="speech-inspector__quiet-grid">
        <label>开始<input type="time" :value="config.trigger.window_start ?? ''" @change="updateTrigger({ window_start: ($event.target as HTMLInputElement).value || null })" /></label>
        <label>结束<input type="time" :value="config.trigger.window_end ?? ''" @change="updateTrigger({ window_end: ($event.target as HTMLInputElement).value || null })" /></label>
      </div>
      <div class="speech-inspector__quiet-heading"><strong>安静时段</strong><span>按组件时区执行</span></div>
      <div class="speech-inspector__quiet-grid">
        <label>开始<input type="time" :value="config.quiet_start ?? ''" @change="update({ quiet_start: ($event.target as HTMLInputElement).value || null })" /></label>
        <label>结束<input type="time" :value="config.quiet_end ?? ''" @change="update({ quiet_end: ($event.target as HTMLInputElement).value || null })" /></label>
      </div>
      <label>安静时段行为<select :value="config.quiet_mode" @change="update({ quiet_mode: ($event.target as HTMLSelectElement).value })"><option value="mute">静默且不播报</option><option value="delay">延迟到安静时段后</option><option value="subtitle">仅更新字幕</option></select></label>
    </details>
    <details>
      <summary>字幕</summary>
      <label class="check"><input type="checkbox" :checked="config.subtitle_enabled" @change="update({ subtitle_enabled: ($event.target as HTMLInputElement).checked })" />显示字幕</label>
      <label>位置<select :value="config.subtitle_position" @change="update({ subtitle_position: ($event.target as HTMLSelectElement).value })"><option value="bottom">底部</option><option value="top">顶部</option></select></label>
      <label>字幕颜色<input type="color" :value="config.subtitle_color" @change="update({ subtitle_color: ($event.target as HTMLInputElement).value })" /></label>
      <label>字幕背景<input type="color" :value="config.subtitle_background.slice(0, 7)" @change="update({ subtitle_background: ($event.target as HTMLInputElement).value + 'B8' })" /></label>
      <label>字幕换行<select :value="config.subtitle_scroll" @change="update({ subtitle_scroll: ($event.target as HTMLSelectElement).value })"><option value="wrap">自动换行</option><option value="scroll">滚动显示</option></select></label>
      <label>字号<input type="number" min="12" max="80" :value="config.subtitle_font_size" @change="update({ subtitle_font_size: Number(($event.target as HTMLInputElement).value) })" /></label>
      <label>最大行数<input type="number" min="1" max="10" :value="config.subtitle_max_lines" @change="update({ subtitle_max_lines: Number(($event.target as HTMLInputElement).value) })" /></label>
    </details>
    <details>
      <summary>高级</summary>
      <label class="check"><input type="checkbox" :checked="config.enabled" @change="update({ enabled: ($event.target as HTMLInputElement).checked })" />启用数字人</label>
      <label>队列策略<select :value="config.queue_policy" @change="update({ queue_policy: ($event.target as HTMLSelectElement).value })"><option value="queue">排队</option><option value="merge">合并待播任务</option><option value="drop_old">丢弃旧待播任务</option><option value="interrupt">打断当前任务</option></select></label>
      <label>最长播报（秒）<input type="number" min="1" max="300" :value="config.max_duration_seconds" @change="update({ max_duration_seconds: Number(($event.target as HTMLInputElement).value) })" /></label>
      <label>队列上限<input type="number" min="1" max="20" :value="config.max_queue_length" @change="update({ max_queue_length: Number(($event.target as HTMLInputElement).value) })" /></label>
      <label>过期时间（秒）<input type="number" min="10" max="86400" :value="config.stale_after_seconds" @change="update({ stale_after_seconds: Number(($event.target as HTMLInputElement).value) })" /></label>
    </details>
  </div>
</template>

<style scoped>
.speech-inspector { display: grid; gap: 8px; min-width: 0; }
details { border-top: 1px solid var(--dp-border, #d7dce2); padding-top: 8px; }
summary { cursor: pointer; font-size: 12px; font-weight: 600; margin-bottom: 8px; }
label { display: grid; gap: 4px; font-size: 11px; margin: 8px 0; min-width: 0; }
input, textarea, select { box-sizing: border-box; width: 100%; min-width: 0; padding: 6px; color: inherit; background: var(--dp-surface, #fff); border: 1px solid var(--dp-border, #b8c1cb); border-radius: 4px; font: inherit; }
input[type="range"] { padding: 0; }
.check { display: flex; align-items: center; }
.check input { width: auto; }
button { display: inline-flex; align-items: center; gap: 4px; padding: 5px 8px; color: inherit; background: transparent; border: 1px solid var(--dp-border, #b8c1cb); border-radius: 4px; cursor: pointer; font-size: 11px; }
.speech-inspector__actions, .speech-inspector__asset, .speech-inspector__variable { display: flex; align-items: center; gap: 6px; min-width: 0; }
.speech-inspector__condition-heading { display: flex; align-items: center; justify-content: space-between; gap: 6px; margin: 6px 0; font-size: 11px; }
.speech-inspector__condition { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr) auto; align-items: center; gap: 4px; margin: 5px 0; }
.speech-inspector__condition input, .speech-inspector__condition select { min-width: 0; }
.speech-inspector__condition button { width: 28px; height: 28px; padding: 0; justify-content: center; }
.speech-inspector__mapping-heading, .speech-inspector__mapping-title { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
.speech-inspector__mapping-heading span { color: var(--dp-muted, #6b7280); font-size: 10px; }
.speech-inspector__script { display: grid; gap: 6px; padding: 8px; border: 1px solid var(--dp-border, #d7dce2); border-radius: 4px; }
.speech-inspector__script-row { display: grid; grid-template-columns: 88px minmax(0, 1fr) auto; align-items: center; gap: 5px; min-width: 0; }
.speech-inspector__script-row textarea, .speech-inspector__script-row input { min-width: 0; }
.speech-inspector__script-row > label { min-width: 0; }
.speech-inspector__script-row > button { width: 28px; height: 28px; padding: 0; justify-content: center; }
.speech-inspector__ai-diff { display: grid; gap: 5px; margin: 6px 0; font-size: 11px; }
.speech-inspector__ai-diff > div { display: grid; grid-template-columns: 34px minmax(0, 1fr); gap: 6px; min-width: 0; }
.speech-inspector__ai-diff span { color: var(--dp-muted, #6b7280); }
.speech-inspector__ai-diff del, .speech-inspector__ai-diff ins { padding: 4px; overflow-wrap: anywhere; text-decoration: none; border-radius: 3px; }
.speech-inspector__ai-diff del { color: #9f3a38; background: #fff1f0; }
.speech-inspector__ai-diff ins { color: #17633a; background: #edfff3; }
.speech-inspector__ai-actions { display: flex; flex-wrap: wrap; gap: 6px; }
.speech-inspector__quiet-heading { display: flex; justify-content: space-between; align-items: baseline; margin-top: 10px; font-size: 11px; }
.speech-inspector__quiet-heading span { color: var(--dp-muted, #6b7280); font-size: 10px; }
.speech-inspector__quiet-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.speech-inspector__mapping { padding: 7px; margin-top: 6px; border: 1px solid var(--dp-border, #d7dce2); border-radius: 4px; }
.speech-inspector__mapping-title { overflow-wrap: anywhere; font-size: 11px; }
.speech-inspector__mapping-title button { width: 26px; height: 26px; padding: 0; justify-content: center; }
.speech-inspector__actions label, .speech-inspector__asset label:first-child { flex: 1; min-width: 0; }
.speech-inspector__variable { flex-wrap: wrap; font-size: 11px; overflow-wrap: anywhere; margin-bottom: 6px; }
.speech-inspector__variable span { flex: 1; }
.speech-inspector__ai { padding: 7px; border: 1px solid var(--dp-border, #d7dce2); border-radius: 4px; }
.speech-inspector__preview { display: grid; gap: 6px; padding: 8px; margin-top: 8px; border: 1px solid var(--dp-border, #d7dce2); border-radius: 4px; background: color-mix(in srgb, var(--dp-accent, #1c8a78) 5%, transparent); }
.speech-inspector__preview-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 6px; font-size: 11px; }
.speech-inspector__preview-heading span { color: var(--dp-muted, #6b7280); font-size: 10px; }
.speech-inspector__preview-text { min-height: 36px; margin: 0; padding: 6px; white-space: pre-wrap; overflow-wrap: anywhere; background: var(--dp-surface, #fff); border: 1px solid var(--dp-border, #d7dce2); border-radius: 3px; }
.speech-inspector__tts { display: grid; gap: 5px; padding-top: 6px; border-top: 1px solid var(--dp-border, #d7dce2); }
.speech-inspector__tts audio { width: 100%; min-width: 0; }
.speech-inspector__ai summary { display: flex; align-items: center; gap: 5px; }
.speech-inspector__ai-context { margin: 5px 0; color: var(--dp-muted, #64737d); font-size: 10px; overflow-wrap: anywhere; }
.speech-inspector__ai-result { display: grid; gap: 6px; margin-top: 8px; padding: 8px; border-left: 2px solid var(--dp-accent, #1c8a78); background: color-mix(in srgb, var(--dp-accent, #1c8a78) 8%, transparent); }
.speech-inspector__ai-result p { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; }
.speech-inspector__ai-result ul { margin: 0; padding-left: 16px; color: var(--dp-muted, #64737d); font-size: 10px; }
.speech-inspector__ai-error { color: var(--dp-danger, #c03938); overflow-wrap: anywhere; font-size: 11px; }
.speech-inspector__upload { position: relative; display: grid; place-items: center; width: 28px; height: 28px; border: 1px solid var(--dp-border, #b8c1cb); border-radius: 4px; overflow: hidden; cursor: pointer; }
.speech-inspector__upload input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
p[role="alert"] { color: var(--dp-danger, #c03938); overflow-wrap: anywhere; font-size: 11px; }
</style>
