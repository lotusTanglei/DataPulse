<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";

import type { JsonValue, QueryResult } from "../../query/types";
import type { ComponentInstance, LoadAsset, RuntimeMode } from "../types";
import { numberProp, stringProp } from "./format";

const props = defineProps<{
  instance: ComponentInstance;
  result: QueryResult | null;
  loading: boolean;
  error: unknown | null;
  loadAsset: LoadAsset;
  mode?: RuntimeMode;
}>();

const mediaUrl = ref("");
const assetError = ref(false);
const slideIndex = ref(0);
let controller: AbortController | null = null;
let timer: ReturnType<typeof setInterval> | null = null;

const assetId = computed(() => stringProp(props.instance.props, "asset_id").trim());
const title = computed(() => stringProp(props.instance.props, "title"));
const safeUrl = computed(() => {
  const candidate = stringProp(props.instance.props, "url").trim();
  if (!candidate) return "";
  try {
    const parsed = new URL(candidate, window.location.origin);
    return parsed.protocol === "https:" || parsed.protocol === "http:" ? parsed.href : "";
  } catch {
    return "";
  }
});
const slides = computed(() => {
  const value = props.instance.props?.screen_urls;
  const candidates: JsonValue[] = Array.isArray(value)
    ? value
    : typeof value === "string"
      ? value.split(/\r?\n/).map((item) => item.trim()).filter(Boolean)
      : [];
  return candidates.flatMap((item: JsonValue) => {
    if (typeof item !== "string") return [];
    try {
      const parsed = new URL(item, window.location.origin);
      return parsed.protocol === "https:" || parsed.protocol === "http:" ? [parsed.href] : [];
    } catch {
      return [];
    }
  }).slice(0, 12);
});
const activeSlide = computed(() => slides.value[slideIndex.value] ?? "");

async function loadMedia(): Promise<void> {
  controller?.abort();
  assetError.value = false;
  if (mediaUrl.value.startsWith("blob:")) URL.revokeObjectURL(mediaUrl.value);
  mediaUrl.value = "";
  if (!assetId.value) return;
  const next = new AbortController();
  controller = next;
  try {
    const loaded = await props.loadAsset(assetId.value, next.signal);
    if (!next.signal.aborted && controller === next) mediaUrl.value = loaded;
  } catch {
    if (!next.signal.aborted && controller === next) assetError.value = true;
  }
}

function resetCarousel(): void {
  if (timer) clearInterval(timer);
  timer = null;
  slideIndex.value = 0;
  if (slides.value.length < 2 || props.mode === "editor") return;
  const interval = numberProp(props.instance.props, "interval_seconds", 10, { min: 5, max: 120 });
  timer = setInterval(() => {
    slideIndex.value = (slideIndex.value + 1) % slides.value.length;
  }, interval * 1000);
}

watch([assetId, () => props.loadAsset], () => void loadMedia(), { immediate: true });
watch([slides, () => props.mode, () => props.instance.props?.interval_seconds], resetCarousel, { immediate: true });
onBeforeUnmount(() => {
  controller?.abort();
  if (timer) clearInterval(timer);
  if (mediaUrl.value.startsWith("blob:")) URL.revokeObjectURL(mediaUrl.value);
});
</script>

<template>
  <section class="media-embed" :data-variant="instance.type">
    <strong v-if="title" class="media-embed__title">{{ title }}</strong>
    <p v-if="error || assetError" role="status">媒体加载失败</p>
    <template v-else-if="instance.type === 'builtin.video'">
      <video
        v-if="mediaUrl"
        :src="mediaUrl"
        :autoplay="instance.props?.autoplay === true"
        :muted="instance.props?.muted !== false"
        :loop="instance.props?.loop === true"
        controls
        playsinline
      />
      <p v-else role="status">请选择视频资源</p>
    </template>
    <template v-else-if="instance.type === 'builtin.iframe'">
      <iframe
        v-if="safeUrl"
        :src="safeUrl"
        :title="title || '嵌入内容'"
        loading="lazy"
        referrerpolicy="no-referrer"
        sandbox="allow-forms allow-popups allow-scripts allow-same-origin"
      />
      <p v-else role="status">请输入 HTTP(S) 地址</p>
    </template>
    <template v-else>
      <iframe
        v-if="activeSlide"
        :key="activeSlide"
        :src="activeSlide"
        :title="title || '多屏轮播'"
        loading="lazy"
        referrerpolicy="no-referrer"
        sandbox="allow-scripts allow-same-origin"
      />
      <p v-else role="status">请配置轮播大屏地址</p>
      <nav v-if="slides.length > 1" aria-label="轮播分页">
        <button
          v-for="(_, index) in slides"
          :key="index"
          type="button"
          :aria-label="`显示第 ${index + 1} 屏`"
          :aria-current="index === slideIndex ? 'true' : undefined"
          @click="slideIndex = index"
        />
      </nav>
    </template>
  </section>
</template>

<style scoped>
.media-embed { position: relative; display: grid; width: 100%; height: 100%; min-height: 0; place-items: center; overflow: hidden; color: var(--screen-text-primary, #eaf4ff); }
.media-embed video, .media-embed iframe { width: 100%; height: 100%; border: 0; object-fit: cover; background: #050a0f; }
.media-embed__title { position: absolute; z-index: 2; top: 10px; left: 12px; padding: 4px 7px; background: rgb(5 10 15 / 72%); font-size: 11px; pointer-events: none; }
.media-embed p { margin: 0; color: var(--screen-text-secondary, #94a3b8); font-size: 12px; }
.media-embed nav { position: absolute; z-index: 3; right: 12px; bottom: 10px; display: flex; gap: 6px; }
.media-embed nav button { width: 8px; height: 8px; padding: 0; border: 1px solid var(--screen-accent, #26d9c1); border-radius: 50%; background: transparent; cursor: pointer; }
.media-embed nav button[aria-current="true"] { background: var(--screen-accent, #26d9c1); }
</style>
