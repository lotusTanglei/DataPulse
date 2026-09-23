import {
  inject,
  onScopeDispose,
  provide,
  shallowRef,
  watch,
  type InjectionKey,
  type ShallowRef,
} from "vue";
import type { DashboardDocument } from "../../contracts";
import {
  defaultComponentRegistry,
  type ComponentRegistry,
} from "../runtime/registry";
import { getPackage, importAdminPlugin } from "./api";
import { createPluginRegistry } from "./plugins";

const key: InjectionKey<ShallowRef<ComponentRegistry>> = Symbol(
  "document-plugin-registry",
);
export function provideEditorPlugins(document: () => DashboardDocument | null) {
  const registry = shallowRef(defaultComponentRegistry);
  let controller: AbortController | null = null;
  provide(key, registry);
  watch(
    () => JSON.stringify(document()?.plugin_dependencies ?? []),
    async () => {
      controller?.abort();
      const next = new AbortController();
      controller = next;
      registry.value = defaultComponentRegistry;
      const dependencies = document()?.plugin_dependencies ?? [];
      if (!dependencies.length) return;
      const packages = await Promise.all(
        dependencies.map(async (item) => {
          try {
            return await getPackage(
              "plugin",
              item.id,
              item.version,
              next.signal,
            );
          } catch {
            return null;
          }
        }),
      );
      if (next.signal.aborted) return;
      const loaded = await createPluginRegistry(
        packages.filter((item) => item !== null),
        (item) => importAdminPlugin(item, next.signal),
      );
      if (!next.signal.aborted) registry.value = loaded;
    },
    { immediate: true },
  );
  onScopeDispose(() => controller?.abort());
  return registry;
}
export function useEditorRegistry() {
  return inject(key, shallowRef(defaultComponentRegistry));
}
