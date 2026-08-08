import { expect, test } from "vitest";

import {
  alignFrames,
  distributeFrames,
  selectionBounds,
  snapFrame,
} from "./geometry";

const canvas = { width: 1920, height: 1080 };

test("snaps to canvas edges, grid, sibling guides, and reports overlap", () => {
  const result = snapFrame(
    { id: "moving", frame: { x: 96, y: 198, width: 100, height: 80 } },
    {
      canvas,
      siblings: [
        { id: "sibling", frame: { x: 210, y: 200, width: 120, height: 80 } },
      ],
      gridSize: 10,
      threshold: 8,
    },
  );

  expect(result.frame).toMatchObject({ x: 100, y: 200 });
  expect(result.guides).toEqual(
    expect.arrayContaining([
      expect.objectContaining({ orientation: "horizontal", position: 200 }),
    ]),
  );
  expect(result.overlapIds).toEqual([]);

  const overlapping = snapFrame(
    { id: "moving", frame: { x: 205, y: 205, width: 100, height: 80 } },
    { canvas, siblings: [{ id: "sibling", frame: { x: 210, y: 200, width: 120, height: 80 } }] },
  );
  expect(overlapping.overlapIds).toEqual(["sibling"]);
});

test("clamps snapped frames to the fixed canvas", () => {
  const result = snapFrame(
    { id: "moving", frame: { x: 1900, y: 1070, width: 100, height: 80 } },
    { canvas, siblings: [], gridSize: 10, threshold: 8 },
  );

  expect(result.frame).toMatchObject({ x: 1820, y: 1000 });
});

test("calculates selection bounds, alignment, and equal distribution", () => {
  const items = [
    { id: "a", frame: { x: 0, y: 20, width: 100, height: 40 } },
    { id: "b", frame: { x: 240, y: 80, width: 80, height: 60 } },
    { id: "c", frame: { x: 500, y: 140, width: 120, height: 80 } },
  ];

  expect(selectionBounds(items.map((item) => item.frame))).toEqual({
    x: 0,
    y: 20,
    width: 620,
    height: 200,
  });
  expect(alignFrames(items, "top")).toEqual({
    a: { y: 20 },
    b: { y: 20 },
    c: { y: 20 },
  });
  expect(distributeFrames(items, "horizontal")).toEqual({
    a: {},
    b: { x: 260 },
    c: {},
  });
});
