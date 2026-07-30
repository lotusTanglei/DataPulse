<script setup lang="ts">
import {
  computed,
  onBeforeUnmount,
  ref,
  watch,
  type CSSProperties,
} from "vue";

import type { QueryResult } from "../../query/types";
import type { ComponentInstance, LoadAsset } from "../types";
import { stringProp } from "./format";

const props = defineProps<{
  instance: ComponentInstance;
  result: QueryResult | null;
  loading: boolean;
  error: unknown | null;
  loadAsset: LoadAsset;
}>();

const source = ref("");
const loadingAsset = ref(false);
const assetFailed = ref(false);
let controller: AbortController | null = null;

const assetId = computed(() =>
  stringProp(props.instance.props, "asset_id").trim(),
);
const alt = computed(() => stringProp(props.instance.props, "alt"));
const fit = computed(() => {
  const value = stringProp(props.instance.props, "fit", "cover");
  return ["contain", "cover", "fill", "none", "scale-down"].includes(value)
    ? value
    : "cover";
});
const imageStyle = computed<CSSProperties>(() => ({
  objectFit: fit.value as CSSProperties["objectFit"],
}));

function releaseSource(): void {
  if (source.value.startsWith("blob:")) {
    URL.revokeObjectURL(source.value);
  }
  source.value = "";
}

async function load(): Promise<void> {
  controller?.abort();
  releaseSource();
  assetFailed.value = false;
  if (!assetId.value) {
    loadingAsset.value = false;
    return;
  }
  const nextController = new AbortController();
  controller = nextController;
  loadingAsset.value = true;
  try {
    const loaded = await props.loadAsset(assetId.value, nextController.signal);
    if (!nextController.signal.aborted && controller === nextController) {
      source.value = loaded;
    }
  } catch {
    if (!nextController.signal.aborted && controller === nextController) {
      assetFailed.value = true;
    }
  } finally {
    if (controller === nextController) {
      loadingAsset.value = false;
    }
  }
}

watch([assetId, () => props.loadAsset], () => void load(), {
  immediate: true,
});

onBeforeUnmount(() => {
  controller?.abort();
  releaseSource();
});
</script>

<template>
  <div class="screen-image">
    <p v-if="loadingAsset" class="screen-component-state" role="status">
      正在加载图片…
    </p>
    <p v-else-if="assetFailed" class="screen-component-state" role="status">
      图片加载失败
    </p>
    <p v-else-if="!assetId" class="screen-component-state" role="status">
      请选择图片
    </p>
    <img
      v-else-if="source"
      :src="source"
      :alt="alt"
      :style="imageStyle"
    />
  </div>
</template>

<style scoped>
.screen-image {
  display: grid;
  width: 100%;
  height: 100%;
  overflow: hidden;
  place-items: center;
  background: var(--screen-component-surface, transparent);
}

.screen-image img {
  display: block;
  width: 100%;
  height: 100%;
}

.screen-component-state {
  margin: 0;
  color: var(--screen-text-secondary, #94a3b8);
  font-size: 13px;
}
</style>
