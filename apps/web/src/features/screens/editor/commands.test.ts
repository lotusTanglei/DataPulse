import type { DashboardDocument } from "../../../contracts";
import { expect, test } from "vitest";

import {
  applyCommand,
  EditorCommandError,
  type EditorCommand,
} from "./commands";
import { snapToGrid, translateFrame } from "./geometry";
import { EditorHistory } from "./history";

function documentWithText(): DashboardDocument {
  return {
    schema_version: 1,
    canvas: { width: 1920, height: 1080, background: {} },
    theme: { id: "datapulse-dark", tokens: {} },
    refresh: { mode: "disabled", interval_seconds: null },
    parameters: [],
    components: [
      {
        id: "text-1",
        type: "builtin.text",
        frame: { x: 40, y: 40, width: 320, height: 120, z_index: 0 },
        state: { locked: false, hidden: false },
        props: { text: "原始文本" },
        style: {},
        data_binding: {},
        interactions: [],
      },
    ],
  };
}

test("undo restores the exact document before a frame update", () => {
  const initial = documentWithText();
  const history = new EditorHistory(initial);

  history.execute({
    type: "update_frame",
    component_ids: ["text-1"],
    patch: { x: 120, y: 80 },
  });

  expect(history.current.components?.[0]?.frame.x).toBe(120);
  expect(initial.components?.[0]?.frame.x).toBe(40);
  history.undo();
  expect(history.current).toEqual(initial);
  history.redo();
  expect(history.current.components?.[0]?.frame.x).toBe(120);
});

test("component commands add, duplicate, patch, reorder, lock, hide, and remove", () => {
  const commands: EditorCommand[] = [
    {
      type: "add_component",
      component: {
        id: "chart-1",
        type: "builtin.line",
        frame: { x: 400, y: 40, width: 640, height: 320, z_index: 1 },
        state: { locked: false, hidden: false },
        props: {},
        style: {},
        data_binding: {},
        interactions: [],
      },
    },
    {
      type: "duplicate_components",
      source_ids: ["text-1"],
      id_map: { "text-1": "text-copy" },
      offset: { x: 20, y: 20 },
    },
    {
      type: "update_props",
      component_id: "text-copy",
      patch: { text: "复制文本" },
    },
    {
      type: "update_style",
      component_id: "text-copy",
      patch: { color: "#fff" },
    },
    {
      type: "set_component_state",
      component_ids: ["text-copy"],
      patch: { locked: true, hidden: true },
    },
    {
      type: "reorder_components",
      component_ids: ["chart-1", "text-copy", "text-1"],
    },
    {
      type: "remove_components",
      component_ids: ["chart-1"],
    },
  ];

  const result = commands.reduce(applyCommand, documentWithText());

  expect(result.components?.map((component) => component.id)).toEqual([
    "text-copy",
    "text-1",
  ]);
  expect(result.components?.[0]).toMatchObject({
    frame: { x: 60, y: 60 },
    props: { text: "复制文本" },
    style: { color: "#fff" },
    state: { locked: true, hidden: true },
  });
});

test("group commands preserve component data and can be undone", () => {
  const initial = documentWithText();
  initial.components!.push({
    id: "text-2",
    type: "builtin.text",
    frame: { x: 400, y: 40, width: 320, height: 120, z_index: 1 },
    state: { locked: false, hidden: false },
    props: { text: "第二个文本" },
    style: { color: "#fff" },
    data_binding: {},
    interactions: [],
  });
  const history = new EditorHistory(initial);
  history.execute({
    type: "group_components",
    component_ids: ["text-1", "text-2"],
    group_id: "group-1",
  });
  expect(history.current.components?.map((item) => item.state?.group_id)).toEqual([
    "group-1",
    "group-1",
  ]);
  expect(history.current.components?.[1]?.style).toEqual({ color: "#fff" });
  history.execute({
    type: "ungroup_components",
    component_ids: ["text-1", "text-2"],
  });
  expect(history.current.components?.every((item) => !item.state?.group_id)).toBe(true);
  history.undo();
  expect(history.current.components?.every((item) => item.state?.group_id === "group-1")).toBe(true);
});

test("document commands update canvas, theme, refresh, and parameters immutably", () => {
  const initial = documentWithText();
  const result = [
    {
      type: "update_canvas",
      patch: { width: 1366, height: 768, background: { color: "#111827" } },
    },
    {
      type: "update_theme",
      patch: { id: "brand-dark", tokens: { accent: "#60a5fa" } },
    },
    {
      type: "update_refresh",
      refresh: { mode: "interval", interval_seconds: 30 },
    },
    {
      type: "set_parameters",
      parameters: [
        {
          id: "region",
          name: "region",
          data_type: "string",
          default: "east",
          mutable: true,
          allowed_values: ["east", "west"],
        },
      ],
    },
  ].reduce(
    (document, command) => applyCommand(document, command as EditorCommand),
    initial,
  );

  expect(result.canvas).toMatchObject({ width: 1366, height: 768 });
  expect(result.theme).toMatchObject({ id: "brand-dark" });
  expect(result.refresh).toEqual({ mode: "interval", interval_seconds: 30 });
  expect(result.parameters?.[0]?.name).toBe("region");
  expect(initial.canvas.width).toBe(1920);
});

test("commands reject unknown and duplicate component IDs", () => {
  expect(() =>
    applyCommand(documentWithText(), {
      type: "update_frame",
      component_ids: ["missing"],
      patch: { x: 0 },
    }),
  ).toThrow(EditorCommandError);
  expect(() =>
    applyCommand(documentWithText(), {
      type: "add_component",
      component: documentWithText().components![0]!,
    }),
  ).toThrow(EditorCommandError);
});

test("geometry snaps and keeps translated frames inside the canvas", () => {
  expect(snapToGrid(57, 10)).toBe(60);
  expect(
    translateFrame(
      { x: 1800, y: 1000, width: 200, height: 100, z_index: 0 },
      { x: 90, y: 90 },
      { width: 1920, height: 1080 },
    ),
  ).toMatchObject({ x: 1720, y: 980 });
});
