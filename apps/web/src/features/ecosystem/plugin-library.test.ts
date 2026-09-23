import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, expect, it, vi } from "vitest";
import PluginLibrary from "./PluginLibrary.vue";
import { useScreenEditorStore } from "../screens/editor/store";
import { importAdminPlugin, listPackages } from "./api";
import { getScreen } from "../screens/api";
vi.mock("./api", () => ({ listPackages: vi.fn(), importAdminPlugin: vi.fn() }));
vi.mock("../screens/api", () => ({
  getScreen: vi.fn(),
  updateScreen: vi.fn(),
}));
beforeEach(() => vi.clearAllMocks());
it("clones reactive catalog defaults before adding a pinned component", async () => {
  setActivePinia(createPinia());
  vi.mocked(getScreen).mockResolvedValue({
    id: "screen",
    name: "Board",
    draft_revision: 0,
    draft_document: { canvas: { width: 1000, height: 800 }, components: [] },
  } as never);
  vi.mocked(listPackages).mockResolvedValue([
    {
      kind: "plugin",
      id: "org.example.metrics",
      version: "1.0.0",
      name: "Metrics",
      manifest: {
        components: [
          {
            type: "org.example.metric",
            name: "Metric",
            category: "Data",
            property_schema: {},
            data_schema: {},
            default_props: { label: "Total" },
          },
        ],
      },
    },
  ] as never);
  const store = useScreenEditorStore();
  await store.load("screen");
  const wrapper = mount(PluginLibrary);
  await flushPromises();
  await wrapper.get("button").trigger("click");
  expect(store.document?.components?.[0]?.props).toEqual({ label: "Total" });
  expect(store.document?.plugin_dependencies).toEqual([
    { id: "org.example.metrics", version: "1.0.0" },
  ]);
  wrapper.unmount();
  store.$dispose();
});

async function migrationEditor() {
  setActivePinia(createPinia());
  const document = {
    canvas: { width: 1000, height: 800 },
    plugin_dependencies: [{ id: "org.example.metrics", version: "1.0.0" }],
    components: ["first", "second"].map((id) => ({
      id, type: "org.example.metric", props: { label: id },
      frame: { x: 0, y: 0, width: 100, height: 100 },
    })),
  };
  vi.mocked(getScreen).mockResolvedValue({ id: "screen", name: "Board", draft_revision: 0, draft_document: document, published_document: structuredClone(document) } as never);
  vi.mocked(listPackages).mockResolvedValue(["1.0.0", "2.0.0"].map((version) => ({
    kind: "plugin", id: "org.example.metrics", version, name: "Metrics",
    manifest: { components: [{
      type: "org.example.metric", name: "Metric", category: "Data", default_props: { label: "Default" },
      property_schema: { type: "object", properties: { label: { type: "string" } }, required: ["label"] }, data_schema: {},
    }] },
  })) as never);
  const store = useScreenEditorStore();
  await store.load("screen");
  const wrapper = mount(PluginLibrary);
  await flushPromises();
  return { store, wrapper, document };
}

it("switches every component through the UI in one undoable draft change", async () => {
  vi.mocked(importAdminPlugin).mockResolvedValue({ default: {
    apiVersion: 1, components: { "org.example.metric": {
      mount: vi.fn(), migrate: (props: { label: string }) => ({ label: `${props.label} migrated` }),
    } },
  } });
  const { store, wrapper, document } = await migrationEditor();
  await wrapper.get('[data-action="migrate-plugin"]').trigger("click");
  await flushPromises();
  expect(store.document?.plugin_dependencies?.[0]?.version).toBe("2.0.0");
  expect(store.document?.components?.map((item) => item.props?.label)).toEqual(["first migrated", "second migrated"]);
  expect(store.screen?.published_document).toEqual(document);
  expect(wrapper.text()).toContain("草稿已切换至 2.0.0");
  store.undo();
  expect(store.document).toEqual(document);
  wrapper.unmount();
  store.$dispose();
});

it("reports migration failure without changing any draft state", async () => {
  vi.mocked(importAdminPlugin).mockResolvedValue({ default: {
    apiVersion: 1, components: { "org.example.metric": {
      mount: vi.fn(), migrate: (props: { label: string }) => {
        if (props.label === "second") throw new Error("Cannot migrate second");
        return { label: "changed" };
      },
    } },
  } });
  const { store, wrapper, document } = await migrationEditor();
  await wrapper.get('[data-action="migrate-plugin"]').trigger("click");
  await flushPromises();
  expect(wrapper.get('[role="alert"]').text()).toContain("Cannot migrate second");
  expect(store.document).toEqual(document);
  expect(store.canUndo).toBe(false);
  wrapper.unmount();
  store.$dispose();
});

it("cancels a pending version change on unmount", async () => {
  let finish!: (module: unknown) => void;
  vi.mocked(importAdminPlugin).mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
  const { store, wrapper, document } = await migrationEditor();
  await wrapper.get('[data-action="migrate-plugin"]').trigger("click");
  expect(wrapper.get('[data-action="migrate-plugin"]').attributes("disabled")).toBeDefined();
  const signal = vi.mocked(importAdminPlugin).mock.calls[0]?.[1];
  wrapper.unmount();
  expect(signal?.aborted).toBe(true);
  finish({ default: { apiVersion: 1, components: { "org.example.metric": { mount: vi.fn() } } } });
  await flushPromises();
  expect(store.document).toEqual(document);
  store.$dispose();
});
