import type {
  ChartSpec,
  DashboardDocument,
  EmbedMessageEnvelope,
  EmbedTicketClaims,
} from "./index";

type DashboardFixture = {
  schema_version: 1;
  canvas: {
    width: 1920;
    height: 1080;
    background: { color: "#0b1020" };
  };
  theme: {
    id: "datapulse-dark";
    tokens: { text_primary: "#f8fafc" };
  };
  refresh: { mode: "interval"; interval_seconds: 30 };
  parameters: [
    {
      id: "region";
      name: "region";
      data_type: "string";
      default: "east";
      mutable: true;
      allowed_values: ["east", "west"];
    },
  ];
  components: [
    {
      id: "sales";
      type: "builtin.line";
      frame: {
        x: 40;
        y: 40;
        width: 640;
        height: 320;
        z_index: 1;
      };
      state: { locked: false; hidden: false };
      props: {};
      style: {};
      data_binding: {};
      interactions: [];
    },
  ];
};

type ChartFixture = {
  schema_version: 1;
  dataset_id: "sales";
  dimensions: ["month"];
  measures: [{ field: "amount"; aggregation: "sum" }];
  filters: [
    {
      field: "region";
      operator: "equals";
      value: { kind: "parameter"; name: "region" };
    },
  ];
  sort: [];
  limit: 1000;
  visual: { type: "line"; title: "月度销售趋势" };
};

type EmbedTicketFixture = {
  schema_version: 1;
  issuer: "datapulse";
  audience: "datapulse-embed";
  ticket_id: "ticket-1";
  screen_id: "screen-1";
  allowed_origin: "https://host.example.com";
  issued_at: "2026-07-30T00:00:00Z";
  expires_at: "2026-07-30T01:00:00Z";
  parameters: { region: "east" };
  mutable_parameters: ["region"];
};

type ReadyMessageFixture = {
  type: "ready";
  instance_id: "embed-1";
  protocol_version: 1;
};

type Assert<T extends true> = T;
type DashboardFixtureIsValid = Assert<
  DashboardFixture extends DashboardDocument ? true : false
>;
type ChartFixtureIsValid = Assert<
  ChartFixture extends ChartSpec ? true : false
>;
type EmbedTicketFixtureIsValid = Assert<
  EmbedTicketFixture extends EmbedTicketClaims ? true : false
>;
type ReadyMessageFixtureIsValid = Assert<
  ReadyMessageFixture extends EmbedMessageEnvelope ? true : false
>;

export type {
  ChartFixtureIsValid,
  DashboardFixtureIsValid,
  EmbedTicketFixtureIsValid,
  ReadyMessageFixtureIsValid,
};
