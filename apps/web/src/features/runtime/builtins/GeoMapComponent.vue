<script setup lang="ts">
import { MapChart } from "echarts/charts";
import {
  LegendComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
} from "echarts/components";
import { registerMap, use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { computed, onBeforeUnmount, ref, watch } from "vue";
import VChart from "vue-echarts";

import type { QueryResult } from "../../query/types";
import type { ComponentInstance, LoadAsset } from "../types";
import {
  buildGeoMapOption,
  type ChartTheme,
  type GeoFeatureCollection,
} from "./chartOptions";
import { stringProp } from "./format";
import { DEMO_GEOJSON, DEMO_GEOJSON_MAP_NAME } from "./geoDemo";

use([
  CanvasRenderer,
  LegendComponent,
  MapChart,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
]);

const props = defineProps<{
  instance: ComponentInstance;
  result: QueryResult | null;
  loading: boolean;
  error: unknown | null;
  loadAsset: LoadAsset;
  theme?: ChartTheme;
}>();

const geojson = ref<GeoFeatureCollection | null>(null);
const assetLoading = ref(false);
const assetError = ref(false);
let controller: AbortController | null = null;

const assetId = computed(() =>
  stringProp(props.instance.props, "asset_id").trim(),
);
const isDemoMap = computed(
  () => !assetId.value && props.instance.data_binding?.source === "mock",
);
const mapName = computed(() =>
  isDemoMap.value ? DEMO_GEOJSON_MAP_NAME : `datapulse-map-${assetId.value}`,
);
const emptyText = computed(() =>
  stringProp(props.instance.props, "empty_text", "暂无数据"),
);
const option = computed(() =>
  props.result && geojson.value
    ? buildGeoMapOption(
        props.instance,
        props.result,
        mapName.value,
        geojson.value,
        props.theme ?? {},
      )
    : {},
);

function isFeatureCollection(value: unknown): value is GeoFeatureCollection {
  return (
    value !== null &&
    typeof value === "object" &&
    (value as { type?: unknown }).type === "FeatureCollection" &&
    Array.isArray((value as { features?: unknown }).features)
  );
}

async function loadMap(): Promise<void> {
  controller?.abort();
  geojson.value = null;
  assetError.value = false;
  if (!assetId.value) {
    if (isDemoMap.value) {
      registerMap(DEMO_GEOJSON_MAP_NAME, DEMO_GEOJSON as Parameters<typeof registerMap>[1]);
      geojson.value = DEMO_GEOJSON;
    }
    assetLoading.value = false;
    return;
  }
  const nextController = new AbortController();
  const requestedMapName = mapName.value;
  let loadedUrl = "";
  controller = nextController;
  assetLoading.value = true;
  try {
    loadedUrl = await props.loadAsset(assetId.value, nextController.signal);
    const response = await fetch(loadedUrl, { signal: nextController.signal });
    const payload: unknown = await response.json();
    if (!response.ok || !isFeatureCollection(payload)) {
      throw new Error("Invalid GeoJSON asset.");
    }
    if (!nextController.signal.aborted && controller === nextController) {
      registerMap(
        requestedMapName,
        payload as Parameters<typeof registerMap>[1],
      );
      geojson.value = payload;
    }
  } catch {
    if (!nextController.signal.aborted && controller === nextController) {
      assetError.value = true;
    }
  } finally {
    if (loadedUrl.startsWith("blob:")) {
      URL.revokeObjectURL(loadedUrl);
    }
    if (controller === nextController) {
      assetLoading.value = false;
    }
  }
}

watch([assetId, () => props.loadAsset, () => props.instance.data_binding?.source], () => void loadMap(), {
  immediate: true,
});

onBeforeUnmount(() => controller?.abort());
</script>

<template>
  <div class="screen-map">
    <p v-if="error || assetError" class="screen-component-state" role="status">
      地图加载失败
    </p>
    <p
      v-else-if="loading || assetLoading"
      class="screen-component-state"
      role="status"
    >
      正在加载…
    </p>
    <p
      v-else-if="!result || !geojson || result.rows.length === 0"
      class="screen-component-state"
      role="status"
    >
      {{ assetId ? emptyText : "请选择 GeoJSON 地图" }}
    </p>
    <VChart
      v-else
      class="screen-map__canvas"
      :option="option"
      autoresize
    />
  </div>
</template>

<style scoped>
.screen-map {
  display: grid;
  width: 100%;
  height: 100%;
  min-height: 0;
  place-items: center;
  color: var(--screen-text-primary, #f8fafc);
}

.screen-map__canvas {
  width: 100%;
  height: 100%;
  min-height: 0;
}

.screen-component-state {
  margin: 0;
  color: var(--screen-text-secondary, #94a3b8);
  font-size: 13px;
}
</style>
