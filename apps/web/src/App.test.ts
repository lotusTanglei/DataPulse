import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";

import App from "./App.vue";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("shows the DataPulse title and backend version", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "ok", version: "0.1.0" }),
    }),
  );

  const wrapper = mount(App);
  await flushPromises();

  expect(wrapper.get("h1").text()).toBe("DataPulse");
  expect(wrapper.text()).toContain("Server 0.1.0");
});

test("shows a checking state while the backend request is pending", () => {
  vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));

  const wrapper = mount(App);

  expect(wrapper.text()).toContain("Checking server");
});

test("shows an unavailable state when the backend request fails", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
    }),
  );

  const wrapper = mount(App);
  await flushPromises();

  expect(wrapper.text()).toContain("Server unavailable");
});
