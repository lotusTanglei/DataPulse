<script setup lang="ts">
import { EffectScatterChart, LinesChart, MapChart } from "echarts/charts";
import {
  GeoComponent,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
} from "echarts/components";
import { registerMap, use, type ECElementEvent } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { computed, onBeforeUnmount, ref, watch } from "vue";
import VChart from "vue-echarts";

import type { JsonValue, QueryResult } from "../../query/types";
import type {
  ComponentInstance,
  LoadAsset,
  RuntimeInteraction,
} from "../types";
import { applyChartMotionPreference } from "./chartMotion";
import {
  buildGeoMapOption,
  type GeoFeatureCollection,
} from "./chartOptions";
import { numericValue, stringProp } from "./format";
import { DEMO_GEOJSON, DEMO_GEOJSON_MAP_NAME } from "./geoDemo";

use([
  CanvasRenderer,
  EffectScatterChart,
  GeoComponent,
  GridComponent,
  LegendComponent,
  LinesChart,
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
  theme?: Record<string, JsonValue>;
}>();
const emit = defineEmits<{
  interaction: [interaction: RuntimeInteraction];
}>();

const geojson = ref<GeoFeatureCollection | null>(null);
const assetLoading = ref(false);
const assetError = ref(false);
let controller: AbortController | null = null;

const assetId = computed(() => stringProp(props.instance.props, "asset_id").trim());
const isDemoMap = computed(() => !assetId.value && props.instance.data_binding?.source === "mock");
const mapName = computed(() => isDemoMap.value ? DEMO_GEOJSON_MAP_NAME : `datapulse-map-${assetId.value}`);
const emptyText = computed(() => stringProp(props.instance.props, "empty_text", "暂无数据"));
const title = computed(() => stringProp(props.instance.props, "title"));

function advancedOption() {
  const result = props.result;
  if (!result || !geojson.value) return {};
  if (props.instance.type === "builtin.map_drilldown") {
    return buildGeoMapOption(
      props.instance,
      result,
      mapName.value,
      geojson.value,
      props.theme ?? {},
    );
  }
  const color = typeof props.theme?.accent === "string" ? props.theme.accent : "#26d9c1";
  const base = {
    title: title.value
      ? { text: title.value, left: 14, top: 12, textStyle: { color: "#eaf4ff", fontSize: 14 } }
      : undefined,
    tooltip: { trigger: "item", confine: true },
    geo: {
      map: mapName.value,
      roam: true,
      top: title.value ? 48 : 12,
      bottom: 12,
      itemStyle: { areaColor: "#102b3e", borderColor: "#3a718d", borderWidth: 0.8 },
      emphasis: { itemStyle: { areaColor: "#17445d" } },
    },
  };
  if (props.instance.type === "builtin.bubble_map") {
    return {
      ...base,
      series: [{
        type: "effectScatter",
        coordinateSystem: "geo",
        rippleEffect: { scale: 3 },
        itemStyle: { color },
        data: result.rows.flatMap((row) => {
          const longitude = numericValue(row[1]);
          const latitude = numericValue(row[2]);
          if (longitude === null || latitude === null) return [];
          return [{ name: String(row[0] ?? ""), value: [longitude, latitude, numericValue(row[3]) ?? 1] }];
        }),
        symbolSize: (value: unknown) => {
          const amount = Array.isArray(value) ? numericValue(value[2] as JsonValue) ?? 1 : 1;
          return Math.min(34, 8 + Math.sqrt(Math.max(0, amount)) * 1.5);
        },
      }],
    };
  }
  const lines = result.rows.flatMap((row) => {
    const sourceLng = numericValue(row[1]);
    const sourceLat = numericValue(row[2]);
    const targetLng = numericValue(row[4]);
    const targetLat = numericValue(row[5]);
    if ([sourceLng, sourceLat, targetLng, targetLat].some((value) => value === null)) return [];
    return [{
      fromName: String(row[0] ?? ""),
      toName: String(row[3] ?? ""),
      value: numericValue(row[6]) ?? 1,
      coords: [[sourceLng, sourceLat], [targetLng, targetLat]],
    }];
  });
  return {
    ...base,
    series: [{
      type: "lines",
      coordinateSystem: "geo",
      effect: { show: true, period: 5, trailLength: 0.35, symbolSize: 4 },
      lineStyle: { color, width: 1.5, opacity: 0.75, curveness: 0.2 },
      data: lines,
    }],
  };
}

const option = computed(() => applyChartMotionPreference(advancedOption()));

function isFeatureCollection(value: unknown): value is GeoFeatureCollection {
  return value !== null && typeof value === "object"
    && (value as { type?: unknown }).type === "FeatureCollection"
    && Array.isArray((value as { features?: unknown }).features);
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
  const next = new AbortController();
  const requestedMapName = mapName.value;
  controller = next;
  assetLoading.value = true;
  let loadedUrl = "";
  try {
    loadedUrl = await props.loadAsset(assetId.value, next.signal);
    const response = await fetch(loadedUrl, { signal: next.signal });
    const payload: unknown = await response.json();
    if (!response.ok || !isFeatureCollection(payload)) throw new Error("Invalid GeoJSON asset.");
    if (!next.signal.aborted && controller === next) {
      registerMap(requestedMapName, payload as Parameters<typeof registerMap>[1]);
      geojson.value = payload;
    }
  } catch {
    if (!next.signal.aborted && controller === next) assetError.value = true;
  } finally {
    if (loadedUrl.startsWith("blob:")) URL.revokeObjectURL(loadedUrl);
    if (controller === next) assetLoading.value = false;
  }
}

function handleClick(event: ECElementEvent): void {
  const value = typeof event.name === "string" ? event.name : "";
  if (!value) return;
  const parameter = stringProp(props.instance.props, "drill_parameter", "region");
  emit("interaction", { type: "set_parameter", name: parameter, value });
}

watch([assetId, () => props.loadAsset, () => props.instance.data_binding?.source], () => void loadMap(), { immediate: true });
onBeforeUnmount(() => controller?.abort());
</script>

<template>
  <div class="advanced-geo">
    <p v-if="error || assetError" role="status">地图加载失败</p>
    <p v-else-if="loading || assetLoading" role="status">正在加载…</p>
    <p v-else-if="!result || !geojson || result.rows.length === 0" role="status">{{ assetId || isDemoMap ? emptyText : "请选择 GeoJSON 地图" }}</p>
    <VChart v-else class="advanced-geo__canvas" :option="option" autoresize @click="handleClick" />
  </div>
</template>

<style scoped>
.advanced-geo { display: grid; width: 100%; height: 100%; min-height: 0; place-items: center; color: var(--screen-text-primary, #eaf4ff); }
.advanced-geo__canvas { width: 100%; height: 100%; min-height: 0; }
.advanced-geo p { margin: 0; color: var(--screen-text-secondary, #94a3b8); font-size: 13px; }
</style>
