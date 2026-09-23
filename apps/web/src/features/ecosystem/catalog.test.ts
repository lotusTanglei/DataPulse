import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, expect, it, vi } from "vitest";
import { useAuthStore } from "../../stores/auth";
import CatalogView from "./CatalogView.vue";
import { listPackages, applyTemplate, installPackage } from "./api";
const push = vi.hoisted(() => vi.fn());
vi.mock("vue-router", () => ({ useRouter: () => ({ push }) }));
vi.mock("./api", () => ({
  listPackages: vi.fn(),
  getPackage: vi.fn(),
  installPackage: vi.fn(),
  uninstallPackage: vi.fn(),
  applyTemplate: vi.fn(),
}));
vi.mock("../datasets/api", () => ({
  listDatasets: vi.fn().mockResolvedValue([]),
}));
vi.mock("../screens/assets/api", () => ({
  listAssets: vi.fn().mockResolvedValue([]),
}));
const template = {
  kind: "template" as const,
  id: "org.example.board",
  version: "1.0.0",
  name: "Operations",
  description: "Static dashboard",
  license: "MIT",
  source: "local",
  compatible_api: ">=1,<2",
  sha256: "a".repeat(64),
  installed_at: "2026-09-21",
  files: [],
  manifest: {
    kind: "template" as const,
    id: "org.example.board",
    version: "1.0.0",
    name: "Operations",
    compatible_api: ">=1,<2",
    document: "document.json" as const,
    datasets: [],
    assets: [],
  },
};
beforeEach(() => {
  setActivePinia(createPinia());
  useAuthStore().state = {
    status: "authenticated",
    username: "admin",
    role: "admin",
  };
  vi.clearAllMocks();
  vi.mocked(listPackages).mockResolvedValue([template]);
});
it("shows package provenance and applies an unbound template as a new draft", async () => {
  vi.mocked(applyTemplate).mockResolvedValue({ id: "created" } as never);
  const wrapper = mount(CatalogView);
  await flushPromises();
  await wrapper
    .get('[data-package="org.example.board@1.0.0"]')
    .trigger("click");
  await flushPromises();
  expect(wrapper.text()).toContain("MIT");
  expect(wrapper.text()).toContain("Static dashboard");
  await wrapper.get('[name="screen-name"]').setValue("My board");
  await wrapper.get('[data-action="apply-template"]').trigger("click");
  await flushPromises();
  expect(applyTemplate).toHaveBeenCalledWith(template, {
    name: "My board",
    dataset_mapping: {},
    asset_mapping: {},
  });
  expect(push).toHaveBeenCalledWith({
    name: "screen-edit",
    params: { id: "created" },
  });
  wrapper.unmount();
});
it("requires acknowledging trusted code before installation", async () => {
  const wrapper = mount(CatalogView);
  await flushPromises();
  expect(
    wrapper.get('[data-action="install-package"]').attributes("disabled"),
  ).toBeDefined();
  expect(installPackage).not.toHaveBeenCalled();
  expect(wrapper.text()).toContain("同源");
  wrapper.unmount();
});
it("keeps package code installation unavailable to editors", async () => {
  useAuthStore().state = {
    status: "authenticated",
    username: "editor",
    role: "editor",
  };
  const wrapper = mount(CatalogView);
  await flushPromises();
  expect(wrapper.find('[data-action="install-package"]').exists()).toBe(false);
  expect(wrapper.text()).toContain("Operations");
  wrapper.unmount();
});
