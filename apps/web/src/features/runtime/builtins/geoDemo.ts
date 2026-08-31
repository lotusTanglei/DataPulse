import type { GeoFeatureCollection } from "./chartOptions";

const rectangle = (x: number, y: number, width: number, height: number) => [
  [x, y],
  [x + width, y],
  [x + width, y + height],
  [x, y + height],
  [x, y],
];

export const DEMO_GEOJSON: GeoFeatureCollection = {
  type: "FeatureCollection",
  features: [
    { type: "Feature", properties: { code: "region-1", name: "区域-01" }, geometry: { type: "Polygon", coordinates: [rectangle(0, 30, 25, 25)] } },
    { type: "Feature", properties: { code: "region-2", name: "区域-02" }, geometry: { type: "Polygon", coordinates: [rectangle(28, 34, 24, 21)] } },
    { type: "Feature", properties: { code: "region-3", name: "区域-03" }, geometry: { type: "Polygon", coordinates: [rectangle(56, 28, 22, 27)] } },
    { type: "Feature", properties: { code: "region-4", name: "区域-04" }, geometry: { type: "Polygon", coordinates: [rectangle(5, 2, 25, 22)] } },
    { type: "Feature", properties: { code: "region-5", name: "区域-05" }, geometry: { type: "Polygon", coordinates: [rectangle(34, 5, 25, 22)] } },
    { type: "Feature", properties: { code: "region-6", name: "区域-06" }, geometry: { type: "Polygon", coordinates: [rectangle(63, 1, 27, 23)] } },
  ],
};

export const DEMO_GEOJSON_MAP_NAME = "datapulse-map-demo";
