<script setup lang="ts">
import { ArrowLeft, ArrowRight, Check, FileText, FolderOpen, Image as ImageIcon, Music, RefreshCw, Save, Search, Trash2, Upload, Video, X } from "@lucide/vue";
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { ApiError } from "../../../lib/api";
import InlineNotice from "../../../ui/InlineNotice.vue";
import { assetPreviewUrl, assetUrl, deleteAsset, formatAssetBytes, getAsset, getAssetReferences, getAssetUsage, listAssets, listExpiringAssets, patchAsset, uploadAsset, type AssetType, type ScreenAsset, type ScreenAssetReference, type ScreenAssetUsage } from "./api";

const props = withDefaults(defineProps<{
  selectedId?: string;
  allowedTypes?: AssetType[];
  inUseIds?: string[];
  selectable?: boolean;
}>(), { selectedId: "", allowedTypes: () => [], inUseIds: () => [], selectable: true });
const emit = defineEmits<{ close: []; select: [asset: ScreenAsset]; changed: [asset?: ScreenAsset] }>();
const dialog = ref<HTMLDialogElement>();
const searchInput = ref<HTMLInputElement>();
const uploadInput = ref<HTMLInputElement>();
const replaceInput = ref<HTMLInputElement>();
const assets = ref<ScreenAsset[]>([]);
const selected = ref<ScreenAsset | null>(null);
const references = ref<ScreenAssetReference[]>([]);
const referencesReady = ref(false);
const referencesLoading = ref(false);
const usage = ref<ScreenAssetUsage | null>(null);
const expiringAssets = ref<ScreenAsset[]>([]);
const search = ref("");
const assetType = ref<AssetType | "">(props.allowedTypes.length === 1 ? props.allowedTypes[0]! : "");
const familyId = ref("");
const offset = ref(0);
const pageSize = 24;
const hasMore = ref(false);
const loading = ref(false);
const busy = ref(false);
const error = ref<ApiError | null>(null);
const notice = ref("");
const mediaError = ref(false);
const normalizeLoudness = ref(false);
const trimSilence = ref(false);
const confirmingDelete = ref(false);
const name = ref("");
const licenseNote = ref("");
const licenseExpiry = ref("");
const controller = new AbortController();
let listController: AbortController | null = null;
let referenceController: AbortController | null = null;
let previouslyFocused: HTMLElement | null = null;
const types: { value: AssetType; label: string; icon: typeof ImageIcon; accept: string }[] = [
  { value: "image", label: "图片", icon: ImageIcon, accept: ".png,.jpg,.jpeg,.webp" },
  { value: "video", label: "视频", icon: Video, accept: ".mp4,.webm" },
  { value: "audio", label: "音频", icon: Music, accept: ".mp3,.ogg,.oga,.wav" },
  { value: "subtitle", label: "字幕", icon: FileText, accept: ".vtt" },
  { value: "geojson", label: "地图", icon: FileText, accept: ".geojson,.json" },
];
const uploadAccept = computed(() => types.filter((type) => !props.allowedTypes.length || props.allowedTypes.includes(type.value)).map((type) => type.accept).join(","));
const selectedAllowed = computed(() => selected.value && (!props.allowedTypes.length || props.allowedTypes.includes(selected.value.asset_type)));
const canDelete = computed(() => selected.value && referencesReady.value && !references.value.length && !props.inUseIds.includes(selected.value.id));
const expired = computed(() => selected.value?.license_expires_at && Date.parse(selected.value.license_expires_at) <= Date.now());
const metadataDirty = computed(() => Boolean(selected.value && (
  name.value !== selected.value.name || licenseNote.value !== (selected.value.license_note ?? "") || licenseExpiry.value !== localDate(selected.value.license_expires_at)
)));
const iconFor = (asset: ScreenAsset) => types.find((type) => type.value === asset.asset_type)?.icon ?? FileText;

function localDate(value?: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

function showError(reason: unknown): void {
  if (controller.signal.aborted) return;
  error.value = reason instanceof ApiError ? reason : new ApiError({ code: "ASSET_REQUEST_FAILED", message: "资源操作失败，请重试。", requestId: "", status: 0 });
}

async function choose(asset: ScreenAsset): Promise<void> {
  if (controller.signal.aborted) return;
  stopMedia();
  referenceController?.abort();
  const current = new AbortController();
  referenceController = current;
  selected.value = asset;
  name.value = asset.name;
  licenseNote.value = asset.license_note ?? "";
  licenseExpiry.value = localDate(asset.license_expires_at);
  mediaError.value = false;
  normalizeLoudness.value = false;
  trimSilence.value = false;
  confirmingDelete.value = false;
  references.value = [];
  referencesReady.value = false;
  referencesLoading.value = true;
  try {
    const result = await getAssetReferences(asset.id, current.signal);
    if (!current.signal.aborted) { references.value = result; referencesReady.value = true; }
  } catch (reason) { if (!current.signal.aborted) showError(reason); }
  finally { if (referenceController === current) referencesLoading.value = false; }
}

function requestChoose(asset: ScreenAsset): void {
  if (metadataDirty.value && !window.confirm("放弃未保存的资源信息？")) return;
  void choose(asset);
}

function close(): void {
  if (metadataDirty.value && !window.confirm("放弃未保存的资源信息？")) return;
  emit("close");
}

function stopMedia(): void {
  dialog.value?.querySelectorAll("audio, video").forEach((element) => {
    const media = element as HTMLMediaElement;
    media.pause(); media.removeAttribute("src"); media.load();
  });
}

const previewUrl = computed(() => selected.value ? assetPreviewUrl(selected.value.id, {
  normalizeLoudness: normalizeLoudness.value,
  trimSilence: trimSilence.value,
}) : "");
function changePreviewOption(): void {
  mediaError.value = false;
  stopMedia();
}

async function load(reset = false): Promise<void> {
  if (controller.signal.aborted) return;
  listController?.abort();
  const current = new AbortController();
  listController = current;
  if (reset) offset.value = 0;
  loading.value = true;
  error.value = null;
  try {
    const result = await listAssets({ search: search.value.trim(), assetType: assetType.value, familyId: familyId.value, offset: offset.value, limit: pageSize + 1 }, current.signal);
    if (current.signal.aborted) return;
    assets.value = result.slice(0, pageSize);
    hasMore.value = result.length > pageSize;
  } catch (reason) { if (!current.signal.aborted) showError(reason); }
  finally { if (listController === current) loading.value = false; }
}

async function refreshUsage(): Promise<void> {
  if (controller.signal.aborted) return;
  try { usage.value = await getAssetUsage(controller.signal); }
  catch (reason) { showError(reason); }
}

async function refreshExpiring(): Promise<void> {
  if (controller.signal.aborted) return;
  try { expiringAssets.value = await listExpiringAssets(30, controller.signal); }
  catch (reason) { showError(reason); }
}

async function upload(event: Event, replacement = false): Promise<void> {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file || busy.value || (replacement && !selected.value)) return;
  const replaces = replacement ? selected.value!.id : undefined;
  busy.value = true;
  error.value = null;
  notice.value = "";
  try {
    const asset = await uploadAsset(file, replaces, controller.signal);
    if (controller.signal.aborted) return;
    search.value = "";
    familyId.value = replacement ? asset.family_id : "";
    assetType.value = "";
    await choose(asset);
    await load(true);
    await refreshUsage();
    if (controller.signal.aborted) return;
    notice.value = replacement ? `已创建版本 v${asset.version}` : "资源已入库";
    await nextTick();
    const browser = dialog.value?.querySelector<HTMLElement>(".asset-library__body");
    if (browser) browser.scrollTop = 0;
    dialog.value?.querySelector<HTMLElement>(".asset-library__item.is-selected")?.focus({ preventScroll: true });
    emit("changed", asset);
  } catch (reason) { showError(reason); }
  finally { busy.value = false; input.value = ""; }
}

async function save(): Promise<void> {
  if (!selected.value || busy.value || !name.value.trim()) return;
  busy.value = true;
  error.value = null;
  try {
    const expiry = licenseExpiry.value === localDate(selected.value.license_expires_at)
      ? selected.value.license_expires_at ?? null
      : licenseExpiry.value ? new Date(licenseExpiry.value).toISOString() : null;
    const updated = await patchAsset(selected.value.id, { name: name.value.trim(), license_note: licenseNote.value.trim(), license_expires_at: expiry }, controller.signal);
    if (controller.signal.aborted) return;
    await choose(updated);
    await load();
    if (controller.signal.aborted) return;
    notice.value = "资源信息已保存";
    emit("changed", updated);
  } catch (reason) { showError(reason); }
  finally { busy.value = false; }
}

async function remove(): Promise<void> {
  if (!selected.value || busy.value || !canDelete.value) return;
  busy.value = true;
  error.value = null;
  try {
    await deleteAsset(selected.value.id, controller.signal);
    if (controller.signal.aborted) return;
    stopMedia();
    selected.value = null;
    confirmingDelete.value = false;
    await load(true);
    await refreshUsage();
    if (controller.signal.aborted) return;
    notice.value = "资源已删除";
    emit("changed");
  } catch (reason) { showError(reason); confirmingDelete.value = false; }
  finally { busy.value = false; }
}

function page(direction: number): void { offset.value = Math.max(0, offset.value + direction * pageSize); void load(); }
function versions(): void { familyId.value = selected.value?.family_id ?? ""; search.value = ""; assetType.value = ""; void load(true); }
function select(): void {
  if (!busy.value && selectedAllowed.value && selected.value && !metadataDirty.value) emit("select", selected.value);
}

onMounted(async () => {
  previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  dialog.value?.showModal();
  await nextTick();
  searchInput.value?.focus();
  void load();
  void refreshUsage();
  void refreshExpiring();
  if (props.selectedId) {
    try {
      const asset = await getAsset(props.selectedId, controller.signal);
      if (!controller.signal.aborted && !selected.value) await choose(asset);
    } catch (reason) { showError(reason); }
  }
});
onBeforeUnmount(() => {
  controller.abort();
  listController?.abort();
  referenceController?.abort();
  stopMedia();
  dialog.value?.close();
  previouslyFocused?.focus();
});
</script>

<template>
  <Teleport to="body">
    <dialog ref="dialog" class="dialog-card asset-library" aria-labelledby="asset-library-title" @cancel.prevent="close" @keydown.stop>
      <header class="dialog-heading">
        <h2 id="asset-library-title">媒体资源库</h2>
        <button class="icon-button" type="button" title="关闭资源库" aria-label="关闭资源库" @click="close"><X :size="18" /></button>
      </header>
      <form class="asset-library__toolbar" @submit.prevent="load(true)">
        <label class="asset-library__search"><Search :size="16" aria-hidden="true" /><input ref="searchInput" v-model="search" type="search" aria-label="搜索资源" placeholder="资源名称" maxlength="255" :disabled="busy" /></label>
        <select v-model="assetType" aria-label="资源类型" :disabled="busy" @change="familyId = ''; load(true)"><option value="">全部类型</option><option v-for="type in types" :key="type.value" :value="type.value">{{ type.label }}</option></select>
        <button class="icon-button" type="submit" title="刷新资源" aria-label="刷新资源" :disabled="loading || busy"><RefreshCw :size="16" /></button>
        <button class="secondary-button" type="button" :disabled="busy" @click="uploadInput?.click()"><Upload :size="16" />上传资源</button>
        <input ref="uploadInput" class="asset-library__file" type="file" aria-label="上传资源文件" :accept="uploadAccept" :disabled="busy" @change="upload($event)" />
      </form>
      <div v-if="usage" class="asset-library__usage"><span>{{ usage.asset_count }} 个版本</span><span>{{ formatAssetBytes(usage.size_bytes) }} / {{ formatAssetBytes(usage.max_total_bytes) }}</span><span>总时长 {{ Math.round(usage.duration_seconds) }} / {{ usage.max_total_duration_seconds }} 秒</span></div>
      <InlineNotice v-if="expiringAssets.length" tone="warning"><p>有 {{ expiringAssets.length }} 个资源将在 30 天内到期，请检查授权。</p><button v-if="expiringAssets.length === 1" type="button" class="secondary-button" @click="requestChoose(expiringAssets[0]!)">查看资源</button></InlineNotice>
      <InlineNotice v-if="error" tone="error"><p>{{ error.message }}</p><code>{{ error.code }} {{ error.requestId }}</code></InlineNotice>
      <p v-if="notice || busy" class="asset-library__notice" role="status">{{ busy ? '正在处理资源…' : notice }}</p>
      <div class="asset-library__body">
        <section class="asset-library__browser" aria-label="资源列表" :aria-busy="loading">
          <button v-if="familyId" class="secondary-button" type="button" :disabled="busy" @click="familyId = ''; load(true)"><ArrowLeft :size="14" />全部资源</button>
          <p v-if="loading" role="status">正在加载资源…</p>
          <p v-else-if="!assets.length" class="asset-library__empty">没有匹配的资源</p>
          <ul v-else class="asset-library__list">
            <li v-for="asset in assets" :key="asset.id">
              <button type="button" class="asset-library__item" :class="{ 'is-selected': selected?.id === asset.id }" :aria-pressed="selected?.id === asset.id" :disabled="busy" @click="requestChoose(asset)">
                <img v-if="asset.has_thumbnail" :src="assetUrl(asset.id) + '/thumbnail'" alt="" loading="lazy" />
                <component :is="iconFor(asset)" v-else :size="24" aria-hidden="true" />
                <span><strong>{{ asset.name }}</strong><small>v{{ asset.version }} · {{ formatAssetBytes(asset.size_bytes) }}<template v-if="asset.media?.duration_seconds"> · {{ asset.media.duration_seconds.toFixed(1) }} 秒</template></small></span>
              </button>
            </li>
          </ul>
          <nav class="asset-library__pagination" aria-label="资源分页"><button class="icon-button" type="button" aria-label="上一页资源" title="上一页资源" :disabled="!offset || loading || busy" @click="page(-1)"><ArrowLeft :size="16" /></button><span>第 {{ Math.floor(offset / pageSize) + 1 }} 页</span><button class="icon-button" type="button" aria-label="下一页资源" title="下一页资源" :disabled="!hasMore || loading || busy" @click="page(1)"><ArrowRight :size="16" /></button></nav>
        </section>
        <section class="asset-library__details" aria-label="资源详情">
          <template v-if="selected">
            <div :key="selected.id" class="asset-library__preview">
              <img v-if="selected.asset_type === 'image'" :src="assetUrl(selected.id)" :alt="selected.name" @error="mediaError = true" />
              <video v-else-if="selected.asset_type === 'video'" :key="previewUrl" :src="previewUrl" :poster="selected.has_thumbnail ? assetUrl(selected.id) + '/thumbnail' : undefined" controls playsinline preload="metadata" :aria-label="selected.name" @error="mediaError = true" />
              <audio v-else-if="selected.asset_type === 'audio'" :key="previewUrl" :src="previewUrl" controls preload="metadata" :aria-label="selected.name" @error="mediaError = true" />
              <ol v-else-if="selected.asset_type === 'subtitle'" class="asset-library__cues"><li v-for="cue in selected.media?.cues" :key="cue.start"><time>{{ cue.start.toFixed(3) }} - {{ cue.end.toFixed(3) }}</time><p>{{ cue.text }}</p></li></ol>
              <FileText v-else :size="40" aria-hidden="true" />
            </div>
            <fieldset v-if="selected.asset_type === 'audio' || selected.asset_type === 'video'" class="asset-library__preview-options">
              <legend>预览处理</legend>
              <label><input v-model="normalizeLoudness" type="checkbox" @change="changePreviewOption" />响度归一化</label>
              <label><input v-model="trimSilence" type="checkbox" @change="changePreviewOption" />裁剪首尾静音</label>
            </fieldset>
            <p v-if="mediaError" class="field-error" role="alert">资源无法预览，请检查文件或浏览器格式支持。</p>
            <dl class="asset-library__metadata"><div><dt>格式</dt><dd>{{ selected.mime_type }}</dd></div><div><dt>版本</dt><dd>v{{ selected.version }}</dd></div><div v-if="selected.media?.width"><dt>分辨率</dt><dd>{{ selected.media.width }} × {{ selected.media.height }}</dd></div><div v-if="selected.media?.sample_rate"><dt>音频</dt><dd>{{ selected.media.sample_rate }} Hz · {{ selected.media.channels }} 声道</dd></div><div><dt>上传者</dt><dd>{{ selected.uploaded_by || '未记录' }}</dd></div><div><dt>源文件</dt><dd>{{ selected.original_name }}</dd></div></dl>
            <form class="asset-library__form" @submit.prevent="save">
              <label>资源名称<input v-model="name" maxlength="255" required :disabled="busy" /></label>
              <label>授权备注<textarea v-model="licenseNote" maxlength="2000" rows="2" :disabled="busy" /></label>
              <label>授权到期时间<input v-model="licenseExpiry" type="datetime-local" :disabled="busy" /></label>
              <p v-if="expired" class="field-error" role="status">资源授权已到期</p>
              <div class="asset-library__actions"><button type="submit" class="secondary-button" :disabled="busy || !metadataDirty || !name.trim()"><Save :size="15" />保存信息</button><button class="secondary-button" type="button" :disabled="busy" @click="versions"><FolderOpen :size="15" />版本记录</button><button class="secondary-button" type="button" :disabled="busy" @click="replaceInput?.click()"><Upload :size="15" />上传新版本</button></div>
              <input ref="replaceInput" class="asset-library__file" type="file" aria-label="替换资源文件" :accept="types.find(type => type.value === selected?.asset_type)?.accept" :disabled="busy" @change="upload($event, true)" />
            </form>
            <h3>引用大屏</h3>
            <p v-if="referencesLoading" role="status">正在检查引用…</p>
            <p v-else-if="!referencesReady" role="status">引用检查失败</p>
            <ul v-else-if="references.length" class="asset-library__references"><li v-for="reference in references" :key="reference.screen_id"><span>{{ reference.screen_name }}</span><small>{{ [reference.in_draft ? '草稿' : '', reference.in_published ? '已发布' : ''].filter(Boolean).join(' · ') }}</small></li></ul>
            <p v-else>{{ inUseIds.includes(selected.id) ? '当前编辑草稿已引用' : '未被大屏引用' }}</p>
            <div v-if="confirmingDelete" class="asset-library__delete" role="alert"><p>永久删除“{{ selected.name }}”的 v{{ selected.version }} 版本？</p><button type="button" class="secondary-button" :disabled="busy" @click="confirmingDelete = false">取消删除</button><button type="button" class="danger-button" :disabled="busy || !canDelete" @click="remove">确认删除资源</button></div>
            <button v-else class="icon-button" type="button" title="删除资源版本" aria-label="删除资源版本" :disabled="busy || !canDelete" @click="confirmingDelete = true"><Trash2 :size="16" /></button>
          </template>
          <p v-else class="asset-library__empty">未选择资源</p>
        </section>
      </div>
      <footer class="asset-library__footer"><button class="secondary-button" type="button" @click="close">关闭</button><button v-if="selectable" class="primary-button" type="button" :disabled="busy || !selectedAllowed || metadataDirty" @click="select"><Check :size="16" />使用此版本</button></footer>
    </dialog>
  </Teleport>
</template>

<style scoped>
.asset-library { width: min(1000px, calc(100vw - 32px)); height: min(850px, calc(100dvh - 32px)); max-height: calc(100dvh - 32px); padding: 20px; border-radius: 8px; color: var(--dp-text, #202c35); letter-spacing: 0; overflow: hidden; }
.asset-library[open] { display: flex; flex-direction: column; }
.asset-library > :not(.asset-library__body) { flex-shrink: 0; }
.asset-library::backdrop { background: rgb(15 23 42 / 30%); }
.dialog-heading { margin-bottom: 16px; align-items: center; }
.dialog-heading h2 { font-size: 18px; }
.asset-library__toolbar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.asset-library__search { display: flex; gap: 6px; align-items: center; flex: 1 1 180px; width: auto; min-width: 160px; }
.asset-library input, .asset-library textarea, .asset-library select { min-width: 0; max-width: 100%; padding: 8px; border: 1px solid var(--dp-border, #ccd3d9); border-radius: 4px; background: #fff; color: inherit; font: inherit; }
.asset-library input:not([type="file"]), .asset-library textarea { width: 100%; }
.asset-library__toolbar select { width: auto; flex: 0 1 120px; }
.asset-library button { flex-shrink: 0; min-height: 32px; gap: 6px; letter-spacing: 0; }
.asset-library button:focus-visible, .asset-library input:focus-visible, .asset-library select:focus-visible, .asset-library textarea:focus-visible { outline: 2px solid #147c9c; outline-offset: 2px; }
.asset-library__file { display: none; }
.asset-library__preview-options { display: flex; flex-wrap: wrap; gap: 8px 14px; margin: 10px 0 0; padding: 8px; border: 1px solid var(--dp-border, #ccd3d9); border-radius: 4px; color: var(--dp-muted, #576673); font-size: 12px; }
.asset-library__preview-options legend { padding: 0 4px; }
.asset-library__preview-options label { display: inline-flex; align-items: center; gap: 6px; }
.asset-library__preview-options input { width: 16px; height: 16px; }
.asset-library__usage { display: flex; flex-wrap: wrap; gap: 8px 16px; margin: 12px 0; color: var(--dp-muted, #576673); font-size: 12px; }
.asset-library__body { display: grid; grid-template-columns: minmax(200px, 1fr) minmax(0, 1.2fr); border-top: 1px solid var(--dp-border, #ccd3d9); border-bottom: 1px solid var(--dp-border, #ccd3d9); min-height: 0; flex: 1; overflow: auto; }
.asset-library__browser { min-width: 0; padding: 12px 14px 12px 0; }
.asset-library__list { display: grid; gap: 2px; margin: 8px 0; padding: 0; list-style: none; max-height: 520px; overflow: auto; }
.asset-library__item { display: grid; grid-template-columns: 48px minmax(0, 1fr); align-items: center; width: 100%; min-height: 68px; padding: 8px; border: 1px solid transparent; background: transparent; text-align: left; color: inherit; border-radius: 4px; cursor: pointer; }
.asset-library__item:hover { background: #f2f5f7; }
.asset-library__item.is-selected { border-color: #14847c; background: #eaf5f2; }
.asset-library__item img { width: 48px; height: 48px; object-fit: contain; }
.asset-library__item strong { display: block; font-size: 13px; overflow-wrap: anywhere; }
.asset-library__item small { display: block; color: #576673; margin-top: 4px; font-size: 11px; }
.asset-library__pagination { display: flex; align-items: center; justify-content: space-between; font-size: 12px; }
.asset-library__details { min-width: 0; padding: 16px 0 16px 20px; border-left: 1px solid var(--dp-border, #ccd3d9); overflow-wrap: anywhere; }
.asset-library__preview { display: grid; place-items: center; width: 100%; min-height: 130px; background: #f1f4f6; overflow: hidden; }
.asset-library__preview > img, .asset-library__preview > video { display: block; width: 100%; height: 220px; object-fit: contain; }
.asset-library__preview audio { width: 100%; min-width: 0; }
.asset-library__cues { max-height: 220px; overflow: auto; margin: 0; padding: 16px 32px; width: 100%; }
.asset-library__cues p { white-space: pre-wrap; margin: 4px 0 12px; }
.asset-library__cues time { font-size: 11px; color: #576673; }
.asset-library__metadata { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px; font-size: 12px; }
.asset-library__metadata div { min-width: 0; }
.asset-library__metadata dt { color: #576673; }
.asset-library__metadata dd { margin: 4px 0 0; }
.asset-library__form { display: grid; gap: 10px; font-size: 12px; }
.asset-library__form label { display: grid; gap: 5px; }
.asset-library__actions, .asset-library__footer { display: flex; gap: 8px; flex-wrap: wrap; }
.asset-library__actions button { font-size: 12px; padding: 6px 10px; }
.asset-library__details h3 { font-size: 13px; margin: 18px 0 8px; }
.asset-library__references { padding: 0; list-style: none; font-size: 12px; }
.asset-library__references li { display: flex; justify-content: space-between; gap: 8px; padding: 6px 0; }
.asset-library__references small { flex-shrink: 0; color: #576673; }
.asset-library__details p, .asset-library__notice { font-size: 12px; }
.asset-library__delete { padding: 8px 0; color: #a1273c; }
.asset-library__delete button + button { margin-left: 8px; }
.asset-library__empty { padding: 40px 8px; text-align: center; color: #576673; font-size: 13px; }
.asset-library__footer { justify-content: flex-end; padding-top: 16px; }
@media (max-width: 640px) {
  .asset-library { padding: 12px; width: calc(100vw - 16px); max-height: calc(100dvh - 16px); }
  .asset-library__body { grid-template-columns: minmax(0, 1fr); }
  .asset-library__browser { padding-right: 0; }
  .asset-library__list { max-height: 210px; }
  .asset-library__details { border-left: 0; border-top: 1px solid var(--dp-border, #ccd3d9); padding: 14px 0; }
  .asset-library__toolbar { gap: 6px; }
  .asset-library__toolbar .secondary-button { font-size: 12px; padding: 6px 8px; }
}
</style>
