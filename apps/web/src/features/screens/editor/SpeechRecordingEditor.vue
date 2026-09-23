<script setup lang="ts">
import { Check, FolderOpen, Plus, Trash2 } from "@lucide/vue";
import type { DigitalHumanSpec } from "@datapulse/schema";
import { computed, onBeforeUnmount, ref, watch } from "vue";
import AssetLibraryDialog from "../assets/AssetLibraryDialog.vue";
import { assetUrl, type ScreenAsset } from "../assets/api";

type Recording = NonNullable<DigitalHumanSpec["recording"]>;
type Cue = NonNullable<Recording["cues"]>[number];
const props = defineProps<{ media: ScreenAsset; recording: Recording | null; inUseIds: string[] }>();
const emit = defineEmits<{ confirm: [recording: Recording | null] }>();
const transcript = ref("");
const cues = ref<Cue[]>([]);
const subtitleId = ref("");
const subtitleHash = ref("");
const reviewed = ref(false);
const libraryOpen = ref(false);
const preview = ref<HTMLMediaElement | null>(null);
const previewError = ref(false);
const duration = computed(() => props.media.media?.duration_seconds ?? 0);
const saved = computed(() => props.recording?.transcript === transcript.value.trim() &&
  JSON.stringify(props.recording.cues ?? []) === JSON.stringify(cues.value) &&
  (props.recording.subtitle_asset_id ?? "") === subtitleId.value);
const problem = computed(() => {
  if (!props.media.media?.validated || !props.media.media.audio_codec || !duration.value) return "媒体缺少已验证的音轨或时长";
  if (!transcript.value.trim() || [...transcript.value].length > 4000) return "录制文案应为 1 到 4000 字符";
  if (cues.value.length > 500) return "字幕最多 500 句";
  let previousEnd = 0;
  for (const cue of cues.value) {
    if (![cue.start, cue.end].every(Number.isFinite) || cue.start < previousEnd || cue.end <= cue.start || cue.end > duration.value || !cue.text.trim() || [...cue.text].length > 2000) return "字幕时间必须递增、不重叠且不超过媒体时长，文字不能为空";
    previousEnd = cue.end;
  }
  const normalize = (text: string) => text.trim().replace(/\s+/g, " ");
  if (cues.value.length && !["", " "].some((separator) => normalize(cues.value.map((cue) => cue.text).join(separator)) === normalize(transcript.value))) return "字幕文字与录制文案不一致";
  return "";
});

function stopPreview(): void {
  preview.value?.pause();
  preview.value?.removeAttribute("src");
  preview.value?.load();
}

watch(() => [props.media.id, props.recording], () => {
  const recording = props.recording?.asset_id === props.media.id ? props.recording : null;
  transcript.value = recording?.transcript ?? "";
  cues.value = recording?.cues?.map((cue) => ({ ...cue })) ?? [];
  subtitleId.value = recording?.subtitle_asset_id ?? "";
  subtitleHash.value = recording?.subtitle_sha256 ?? "";
  reviewed.value = false;
}, { immediate: true });

function selectSubtitle(asset: ScreenAsset): void {
  if (asset.asset_type !== "subtitle" || !asset.media?.validated) return;
  cues.value = asset.media.cues?.map((cue) => ({ ...cue })) ?? [];
  transcript.value = cues.value.map((cue) => cue.text).join("\n");
  subtitleId.value = asset.id;
  subtitleHash.value = asset.sha256;
  reviewed.value = false;
  libraryOpen.value = false;
}

function editCues(): void {
  subtitleId.value = "";
  subtitleHash.value = "";
  reviewed.value = false;
}

function addCue(): void {
  const start = cues.value.at(-1)?.end ?? 0;
  cues.value.push({ start, end: Math.min(duration.value, start + 2), text: "" });
  editCues();
}

function confirm(): void {
  if (problem.value || !reviewed.value) return;
  preview.value?.pause();
  emit("confirm", {
    asset_id: props.media.id, sha256: props.media.sha256, duration_seconds: duration.value,
    transcript: transcript.value.trim(), subtitle_asset_id: subtitleId.value,
    subtitle_sha256: subtitleHash.value, cues: cues.value.map((cue) => ({ ...cue })),
  });
}
onBeforeUnmount(stopPreview);
</script>

<template>
  <div class="recording-editor">
    <video v-if="media.asset_type === 'video'" ref="preview" :src="assetUrl(media.id)" controls playsinline preload="metadata" @error="previewError = true" />
    <audio v-else ref="preview" :src="assetUrl(media.id)" controls preload="metadata" @error="previewError = true" />
    <p v-if="previewError" role="alert">媒体预览失败</p>
    <label>录制文案<textarea v-model="transcript" rows="4" maxlength="4000" @input="reviewed = false" /></label>
    <div class="recording-editor__actions">
      <button type="button" @click="($event.currentTarget as HTMLElement).focus(); preview?.pause(); libraryOpen = true"><FolderOpen :size="14" />导入字幕</button>
      <button type="button" title="添加字幕句" aria-label="添加字幕句" :disabled="cues.length >= 500 || (cues.at(-1)?.end ?? 0) >= duration" @click="addCue"><Plus :size="14" /></button>
      <button type="button" title="清除时间轴" aria-label="清除时间轴" :disabled="!cues.length" @click="cues = []; editCues()"><Trash2 :size="14" /></button>
      <output>{{ duration.toFixed(3) }} 秒</output>
    </div>
    <ol class="recording-editor__cues">
      <li v-for="(cue, index) in cues" :key="index">
        <div class="recording-editor__times">
          <label>开始（秒）<input v-model.number="cue.start" type="number" min="0" :max="duration" step="0.001" :aria-label="'字幕 ' + (index + 1) + ' 开始秒数'" @input="editCues" /></label>
          <label>结束（秒）<input v-model.number="cue.end" type="number" min="0" :max="duration" step="0.001" :aria-label="'字幕 ' + (index + 1) + ' 结束秒数'" @input="editCues" /></label>
          <button type="button" :title="'删除字幕 ' + (index + 1)" :aria-label="'删除字幕 ' + (index + 1)" @click="cues.splice(index, 1); editCues()"><Trash2 :size="14" /></button>
        </div>
        <textarea v-model="cue.text" rows="2" maxlength="2000" :aria-label="'字幕 ' + (index + 1) + ' 文字'" @input="editCues" />
      </li>
    </ol>
    <p v-if="problem" role="alert">{{ problem }}</p>
    <label class="recording-editor__review"><input v-model="reviewed" type="checkbox" />已核对录音、文案与字幕</label>
    <div class="recording-editor__actions">
      <button type="button" :disabled="Boolean(problem) || !reviewed" @click="confirm"><Check :size="14" />确认录制内容</button>
      <button v-if="recording" type="button" title="撤销录制确认" aria-label="撤销录制确认" @click="emit('confirm', null)"><Trash2 :size="14" /></button>
      <span v-if="recording" role="status">{{ saved ? '已确认版本' : '修改待确认' }}</span>
    </div>
    <AssetLibraryDialog v-if="libraryOpen" :selected-id="subtitleId" :allowed-types="['subtitle']" :in-use-ids="inUseIds" @close="libraryOpen = false" @select="selectSubtitle" />
  </div>
</template>

<style scoped>
.recording-editor { min-width: 0; font-size: 11px; }
audio, video { display: block; width: 100%; max-height: 200px; }
label { display: grid; gap: 4px; margin: 8px 0; min-width: 0; }
input, textarea { box-sizing: border-box; width: 100%; min-width: 0; padding: 6px; color: inherit; background: var(--dp-surface, #fff); border: 1px solid var(--dp-border, #b8c1cb); border-radius: 4px; font: inherit; }
textarea { resize: vertical; }
button { display: inline-flex; align-items: center; justify-content: center; gap: 4px; min-height: 28px; padding: 4px 6px; color: inherit; background: transparent; border: 1px solid var(--dp-border, #b8c1cb); border-radius: 4px; cursor: pointer; font: inherit; }
button:disabled { opacity: 0.5; cursor: default; }
.recording-editor__actions { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.recording-editor__cues { max-height: 300px; overflow: auto; padding: 0; margin: 8px 0; list-style: none; }
.recording-editor__cues li { padding: 4px 0 8px; border-bottom: 1px solid var(--dp-border, #b8c1cb); }
.recording-editor__times { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 28px; gap: 4px; align-items: center; }
.recording-editor__review { display: flex; align-items: center; }
.recording-editor__review input { width: 14px; height: 14px; flex: none; }
p[role="alert"] { color: var(--dp-danger, #c03938); overflow-wrap: anywhere; }
</style>
