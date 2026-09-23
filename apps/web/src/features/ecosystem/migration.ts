import type { DashboardDocument } from "../../contracts";
import type { EditorCommand } from "../screens/editor/commands";
import type { JsonValue } from "../query/types";
import { readPluginDefinition, type ImportPlugin } from "./plugins";
import { isJsonValue, matchesPluginSchema } from "./schema";
import type { PluginPackage } from "./types";

/** Prepare the whole migration on copies; history applies it only if the draft is unchanged. */
export async function preparePluginMigration(
  document: DashboardDocument,
  current: PluginPackage,
  target: PluginPackage,
  importPlugin: ImportPlugin,
): Promise<EditorCommand> {
  const snapshot = structuredClone(document);
  const pinned = snapshot.plugin_dependencies?.find((item) => item.id === current.id);
  if (current.id !== target.id || pinned?.version !== current.version || current.version === target.version) {
    throw new Error("草稿插件版本已变化，请重新选择版本。");
  }
  const plugin = readPluginDefinition(target, await importPlugin(target));
  const types = new Set(current.manifest.components.map((item) => item.type));
  const properties: Record<string, Record<string, JsonValue>> = {};
  for (const component of snapshot.components ?? []) {
    if (!types.has(component.type)) continue;
    const definition = target.manifest.components.find((item) => item.type === component.type);
    const renderer = plugin.components[component.type];
    if (!definition || !renderer) throw new Error(`目标版本缺少组件：${component.type}`);
    const before = structuredClone(component.props ?? {});
    const after = renderer.migrate ? renderer.migrate(before, current.version) : before;
    if (!after || Array.isArray(after) || typeof after !== "object" || !isJsonValue(after) || !matchesPluginSchema(definition.property_schema, after)) {
      throw new Error(`组件 ${component.id} 的配置不符合目标版本 schema。`);
    }
    properties[component.id] = structuredClone(after);
  }
  return {
    type: "migrate_plugin",
    expected_document: JSON.stringify(snapshot),
    dependency: { id: target.id, version: target.version },
    from_version: current.version,
    properties,
  };
}
