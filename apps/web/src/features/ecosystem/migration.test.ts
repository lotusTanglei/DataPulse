import { describe, expect, it, vi } from "vitest";
import type { PluginDefinition } from "@datapulse/plugin-sdk";
import type { DashboardDocument } from "../../contracts";
import { EditorHistory } from "../screens/editor/history";
import { preparePluginMigration } from "./migration";
import type { PluginPackage } from "./types";

function packageFor(version: string): PluginPackage {
  return {
    kind: "plugin", id: "org.example.metrics", version, name: "Metrics",
    description: "", license: "MIT", source: "local", compatible_api: ">=1,<2",
    sha256: "a".repeat(64), installed_at: "2026-09-21T00:00:00Z", files: [],
    manifest: {
      id: "org.example.metrics", version, name: "Metrics", compatible_api: ">=1,<2", entry: "index.mjs",
      components: [{
        type: "org.example.metric", name: "Metric", category: "Data", default_props: { label: "Total" },
        property_schema: { type: "object", properties: { label: { type: "string" } }, required: ["label"], additionalProperties: false },
        data_schema: {},
      }],
    },
  };
}
const original: DashboardDocument = {
  canvas: { width: 1000, height: 800 },
  plugin_dependencies: [{ id: "org.example.metrics", version: "1.0.0" }],
  components: ["first", "second"].map((id) => ({
    id, type: "org.example.metric", frame: { x: 40, y: 40, width: 320, height: 180 },
    props: { label: id }, data_binding: { source: "fixed", fixed_result: { rows: [[1]] } },
  })),
};
function moduleFor(migrate?: PluginDefinition["components"][string]["migrate"]) {
  return { default: { apiVersion: 1, components: {
    "org.example.metric": { mount: vi.fn(), ...(migrate ? { migrate } : {}) },
  } } };
}

describe("explicit plugin draft migration", () => {
  it("migrates every component in one undoable change and preserves bindings/publication", async () => {
    const document = structuredClone(original);
    const published = structuredClone(document);
    const migrate = vi.fn((props: Record<string, unknown>, _fromVersion: string) => ({ label: `${props.label} v2` }));
    const command = await preparePluginMigration(document, packageFor("1.0.0"), packageFor("2.0.0"), async () => moduleFor(migrate));
    expect(document).toEqual(original);
    const history = new EditorHistory(document);
    const changed = history.execute(command);
    expect(changed.plugin_dependencies?.[0]?.version).toBe("2.0.0");
    expect(changed.components?.map((component) => component.props?.label)).toEqual(["first v2", "second v2"]);
    expect(migrate.mock.calls.map((call) => call[1])).toEqual(["1.0.0", "1.0.0"]);
    expect(changed.components?.[0]?.data_binding).toEqual(original.components?.[0]?.data_binding);
    expect(published).toEqual(original);
    expect(history.undo()).toEqual(original);
    expect(history.redo()).toEqual(changed);
  });

  it("keeps all original props when a later migration mutates then fails", async () => {
    const document = structuredClone(original);
    const migration = preparePluginMigration(document, packageFor("1.0.0"), packageFor("2.0.0"), async () => moduleFor((props) => {
      const previous = props.label;
      props.label = "changed";
      if (previous === "second") throw new Error("Unsupported second component");
      return props;
    }));
    await expect(migration).rejects.toThrow("Unsupported second component");
    expect(document).toEqual(original);
  });

  it("rejects invalid migrated props, removed components, and incompatible modules", async () => {
    await expect(preparePluginMigration(original, packageFor("1.0.0"), packageFor("2.0.0"), async () => moduleFor(() => ({ label: 3 })))).rejects.toThrow(/schema|配置/i);
    const missing = packageFor("2.0.0");
    missing.manifest.components = [];
    await expect(preparePluginMigration(original, packageFor("1.0.0"), missing, async () => moduleFor())).rejects.toThrow(/component|组件/i);
    await expect(preparePluginMigration(original, packageFor("1.0.0"), packageFor("2.0.0"), async () => ({ default: { apiVersion: 2, components: {} } }))).rejects.toThrow(/API/);
    await expect(preparePluginMigration(original, packageFor("1.0.0"), packageFor("2.0.0"), async () => moduleFor(() => ({ label: "ok", bad: undefined }) as never))).rejects.toThrow();
  });

  it("supports schema-compatible downgrade without a migration function", async () => {
    const newer = structuredClone(original);
    newer.plugin_dependencies![0]!.version = "2.0.0";
    const command = await preparePluginMigration(newer, packageFor("2.0.0"), packageFor("1.0.0"), async () => moduleFor());
    expect(new EditorHistory(newer).execute(command)).toEqual(original);
  });

  it("rejects stale preparation after another draft edit without losing that edit", async () => {
    const history = new EditorHistory(original);
    const command = await preparePluginMigration(history.current, packageFor("1.0.0"), packageFor("2.0.0"), async () => moduleFor());
    const edited = history.execute({ type: "update_props", component_id: "first", patch: { label: "Edited while loading" } });
    expect(() => history.execute(command)).toThrow(/changed|变化/);
    expect(history.current).toEqual(edited);
    expect(history.undo()).toEqual(original);
  });
});
