<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, toRaw } from "vue";
import { useScreenEditorStore } from "../screens/editor/store";
import { importAdminPlugin, listPackages } from "./api";
import { preparePluginMigration } from "./migration";
import type { PluginPackage, PluginComponentManifest } from "./types";
const store = useScreenEditorStore();
const packages = ref<PluginPackage[]>([]);
const error = ref("");
const migrationError = ref("");
const migrationStatus = ref("");
const migrating = ref(false);
let migrationController: AbortController | null = null;
async function load() {
  try {
    packages.value = (await listPackages()).filter(
      (item): item is PluginPackage => item.kind === "plugin",
    );
  } catch {
    error.value = "插件目录加载失败";
  }
}
onMounted(load);
onBeforeUnmount(() => migrationController?.abort());
function conflict(item: PluginPackage) {
  return store.document?.plugin_dependencies?.some(
    (dep) => dep.id === item.id && dep.version !== item.version,
  );
}
async function switchVersion(item: PluginPackage) {
  if (!store.document || migrating.value) return;
  const currentVersion = store.document.plugin_dependencies?.find((dep) => dep.id === item.id)?.version;
  const current = packages.value.find((pkg) => pkg.id === item.id && pkg.version === currentVersion);
  if (!current || !conflict(item)) return;
  const screenId = store.screen?.id;
  const controller = new AbortController();
  migrationController = controller;
  migrating.value = true;
  migrationError.value = "";
  migrationStatus.value = "";
  try {
    const command = await preparePluginMigration(
      toRaw(store.document), toRaw(current), toRaw(item),
      (pkg) => importAdminPlugin(pkg, controller.signal),
    );
    if (controller.signal.aborted || store.screen?.id !== screenId) return;
    store.dispatch(command);
    migrationStatus.value = `草稿已切换至 ${item.version}，可撤销。检查后再发布。`;
  } catch (reason) {
    if (!controller.signal.aborted) migrationError.value = reason instanceof Error ? reason.message : "版本切换失败，草稿未改变。";
  } finally {
    migrating.value = false;
  }
}
function add(item: PluginPackage, component: PluginComponentManifest) {
  if (!store.document || conflict(item) || migrating.value) return;
  const id = crypto.randomUUID();
  store.dispatch({
    type: "add_plugin_component",
    dependency: { id: item.id, version: item.version },
    component: {
      id,
      type: component.type,
      frame: {
        x: 40,
        y: 40,
        width: 320,
        height: 180,
        z_index: store.document.components?.length ?? 0,
      },
      props: structuredClone(toRaw(component.default_props ?? {})),
      style: {},
      state: { hidden: false, locked: false },
      data_binding: {},
      interactions: [],
    },
  });
  store.selection = [id];
}
</script>
<template>
  <section class="plugin-library" aria-label="已安装插件">
    <h3>已安装插件</h3>
    <p v-if="error" role="status">
      {{ error }} <button type="button" @click="load">重试</button>
    </p>
    <p v-else-if="!packages.length">在模板与插件目录导入组件包。</p>
    <p v-if="migrationError" role="alert">版本切换失败：{{ migrationError }}</p>
    <p v-if="migrationStatus" role="status">{{ migrationStatus }}</p>
    <div v-for="item in packages" :key="`${item.id}@${item.version}`" :data-plugin-package="`${item.id}@${item.version}`">
      <h4>
        {{ item.name }} <small>{{ item.version }}</small>
      </h4>
      <button v-if="conflict(item)" type="button" data-action="migrate-plugin" :disabled="migrating" @click="switchVersion(item)">
        {{ migrating ? '正在校验迁移…' : `草稿切换至 ${item.version}` }}
      </button>
      <button
        v-for="component in item.manifest.components"
        :key="component.type"
        type="button"
        :disabled="conflict(item) || migrating"
        :title="
          conflict(item) ? '此草稿已使用另一版本，需要显式迁移' : '添加组件'
        "
        @click="add(item, component)"
      >
        {{ component.name }}
      </button>
    </div>
  </section>
</template>
<style scoped>
.plugin-library {
  padding: 12px 0;
  border-top: 1px solid var(--border-color, #333);
  display: grid;
  gap: 8px;
}
.plugin-library h3,
.plugin-library h4,
.plugin-library p {
  margin: 0;
}
.plugin-library p,
.plugin-library small {
  font-size: 12px;
  opacity: 0.7;
}
.plugin-library button {
  margin: 6px 6px 0 0;
  padding: 6px 10px;
  border: 1px solid #66708555;
  border-radius: 6px;
  background: transparent;
  color: inherit;
}
.plugin-library button:disabled {
  opacity: 0.45;
}
</style>
