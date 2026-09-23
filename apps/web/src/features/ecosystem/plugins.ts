import type {
  PluginContext,
  PluginDefinition,
  PluginHandle,
} from "@datapulse/plugin-sdk";
import {
  defineComponent,
  h,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
  type PropType,
} from "vue";
import {
  ComponentRegistry,
  defaultComponentRegistry,
} from "../runtime/registry";
import type { ComponentInstance, PropertyDefinition } from "../runtime/types";
import type { JsonValue, QueryResult } from "../query/types";
import type {
  CatalogPackage,
  PluginComponentManifest,
  PluginPackage,
} from "./types";
import { matchesPluginSchema } from "./schema";

export type ImportPlugin = (package_: PluginPackage) => Promise<unknown>;

export function readPluginDefinition(package_: PluginPackage, imported: unknown): PluginDefinition {
  const plugin = (imported as { default?: PluginDefinition } | null)?.default;
  if (plugin?.apiVersion !== 1 || !plugin.components) throw new Error("Plugin API is incompatible.");
  if (!package_.manifest.components.every((item) => typeof plugin.components[item.type]?.mount === "function")) {
    throw new Error("Plugin renderer does not match its manifest.");
  }
  return plugin;
}

export function schemaProperties(
  schema: Record<string, JsonValue>,
  defaults: Record<string, JsonValue>,
): PropertyDefinition[] {
  const properties = schema.properties;
  if (
    !properties ||
    typeof properties !== "object" ||
    Array.isArray(properties)
  )
    return [];
  return Object.entries(properties).flatMap<PropertyDefinition>(
    ([name, raw]) => {
      if (!raw || typeof raw !== "object" || Array.isArray(raw)) return [];
      const base = {
        name,
        label: typeof raw.title === "string" ? raw.title : name,
        defaultValue: defaults[name] ?? raw.default,
        wide: true,
      };
      if (Array.isArray(raw.enum))
        return [
          {
            ...base,
            editor: "select" as const,
            options: raw.enum.map((value) => ({ label: String(value), value })),
          },
        ];
      if (raw.type === "boolean")
        return [{ ...base, editor: "boolean" as const }];
      if (raw.type === "integer" || raw.type === "number")
        return [
          {
            ...base,
            editor: "number" as const,
            min: typeof raw.minimum === "number" ? raw.minimum : undefined,
            max: typeof raw.maximum === "number" ? raw.maximum : undefined,
            step: raw.type === "integer" ? 1 : 0.1,
          },
        ];
      if (raw.type === "string") return [{ ...base, editor: "text" as const }];
      return [];
    },
  );
}

function pluginWrapper(
  definition: PluginComponentManifest,
  module: PluginDefinition | null,
  failure: unknown,
) {
  return defineComponent({
    name: "TrustedPluginComponent",
    props: {
      instance: { type: Object as PropType<ComponentInstance>, required: true },
      result: { type: Object as PropType<QueryResult | null>, default: null },
      loading: Boolean,
      error: { default: null },
      theme: {
        type: Object as PropType<Record<string, JsonValue>>,
        default: () => ({}),
      },
    },
    setup(props) {
      const element = ref<HTMLElement | null>(null);
      const controller = new AbortController();
      let handle: PluginHandle | null = null;
      function context(): PluginContext {
        if (!matchesPluginSchema(definition.property_schema, props.instance.props ?? {}))
          throw new Error("Plugin properties are invalid.");
        if (props.result && !matchesPluginSchema(definition.data_schema, props.result))
          throw new Error("Plugin data does not match its schema.");
        return {
          instanceId: props.instance.id,
          props: props.instance.props ?? {},
          result: props.result,
          loading: props.loading,
          error: props.error,
          theme: props.theme,
          signal: controller.signal,
        };
      }
      onMounted(() => {
        if (failure) throw failure;
        const renderer = module?.components[definition.type];
        if (!renderer || !element.value)
          throw new Error("Plugin renderer is missing.");
        handle = renderer.mount(element.value, context());
        if (
          !handle ||
          typeof handle.update !== "function" ||
          typeof handle.destroy !== "function"
        ) {
          throw new Error("Plugin lifecycle is invalid.");
        }
      });
      watch(
        () => [
          props.instance,
          props.result,
          props.loading,
          props.error,
          props.theme,
        ],
        () => {
          if (handle) handle.update(context());
        },
        { deep: true },
      );
      onBeforeUnmount(() => {
        controller.abort();
        try {
          handle?.destroy();
        } finally {
          element.value?.replaceChildren();
          handle = null;
        }
      });
      return () =>
        h("div", {
          ref: element,
          class: "plugin-renderer",
          style: { width: "100%", height: "100%" },
        });
    },
  });
}

export async function createPluginRegistry(
  packages: readonly CatalogPackage[],
  importPlugin: ImportPlugin,
): Promise<ComponentRegistry> {
  const registry = new ComponentRegistry();
  for (const definition of defaultComponentRegistry.list())
    registry.register(definition);
  for (const package_ of packages) {
    if (package_.kind !== "plugin") continue;
    let plugin: PluginDefinition | null = null,
      failure: unknown = null;
    try {
      plugin = readPluginDefinition(package_, await importPlugin(package_));
    } catch (reason) {
      failure = reason;
    }
    for (const component of package_.manifest.components) {
      if (registry.has(component.type)) continue;
      registry.register({
        type: component.type,
        label: component.name,
        category: component.category,
        defaultFrame: { width: 320, height: 180 },
        defaultProps: component.default_props ?? {},
        dataCapability: "table",
        demoDataKind: "table",
        propertyGroups: [
          {
            id: "plugin-properties",
            label: `${package_.name} · ${package_.version}`,
            properties: schemaProperties(
              component.property_schema,
              component.default_props ?? {},
            ),
          },
        ],
        component: pluginWrapper(component, plugin, failure),
      });
    }
  }
  return registry;
}

export async function importPluginResponse(
  response: Response,
): Promise<unknown> {
  if (!response.ok) throw new Error("Plugin file unavailable.");
  const source = await response.text();
  const url = URL.createObjectURL(
    new Blob([source], { type: "text/javascript" }),
  );
  try {
    return await import(/* @vite-ignore */ url);
  } finally {
    URL.revokeObjectURL(url);
  }
}
