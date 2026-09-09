import { afterEach, expect, test, vi } from "vitest";

import { applyChartMotionPreference } from "./chartMotion";

afterEach(() => vi.unstubAllGlobals());

test("disables initial and update animations when reduced motion is requested", () => {
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({ matches: true })),
  );

  expect(
    applyChartMotionPreference({
      animation: true,
      animationDuration: 500,
      series: [{ type: "line" }],
    }),
  ).toEqual({
    animation: false,
    animationDuration: 0,
    animationDurationUpdate: 0,
    series: [{ type: "line" }],
  });
});

test("preserves chart options when reduced motion is not requested", () => {
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({ matches: false })),
  );
  const option = { animation: true, animationDuration: 500 };

  expect(applyChartMotionPreference(option)).toBe(option);
});
