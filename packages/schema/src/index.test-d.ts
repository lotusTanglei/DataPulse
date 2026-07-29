import type { ChartSpec } from "./index";

type ChartFixture = {
  schema_version: 1;
  dataset_id: "sales";
  dimensions: ["month"];
  measures: [{ field: "amount"; aggregation: "sum" }];
  filters: [];
  sort: [];
  limit: 1000;
  visual: { type: "line"; title: "月度销售趋势" };
};

type Assert<T extends true> = T;
type ChartFixtureIsValid = Assert<ChartFixture extends ChartSpec ? true : false>;

export type { ChartFixtureIsValid };
