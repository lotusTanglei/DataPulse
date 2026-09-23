<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../../stores/auth";
import { listDatasets } from "../datasets/api";
import { listAssets } from "../screens/assets/api";
import {
  applyTemplate,
  installPackage,
  listPackages,
  uninstallPackage,
} from "./api";
import type { CatalogPackage } from "./types";

const auth = useAuthStore(),
  router = useRouter();
const canAdmin = computed(
  () =>
    auth.state.status === "authenticated" &&
    (auth.state.role ?? "admin") === "admin",
);
const canCreate = computed(
  () => auth.state.status === "authenticated" && auth.state.role !== "viewer",
);
const packages = ref<CatalogPackage[]>([]),
  selected = ref<CatalogPackage | null>(null);
const loading = ref(true),
  busy = ref(false),
  error = ref(""),
  trusted = ref(false),
  file = ref<File | null>(null);
const filter = ref(""),
  kind = ref("all"),
  screenName = ref("");
const datasetMapping = ref<Record<string, string>>({}),
  assetMapping = ref<Record<string, string>>({});
const datasets = ref<Array<{ id: string; name: string }>>([]),
  assets = ref<Array<{ id: string; name: string }>>([]);
const visible = computed(() =>
  packages.value.filter(
    (item) =>
      (kind.value === "all" || item.kind === kind.value) &&
      `${item.name} ${item.id} ${item.description}`
        .toLowerCase()
        .includes(filter.value.toLowerCase()),
  ),
);
const applyReady = computed(
  () =>
    selected.value?.kind === "template" &&
    screenName.value.trim() &&
    selected.value.manifest.datasets.every((id) =>
      datasetMapping.value[id]?.trim(),
    ) &&
    selected.value.manifest.assets.every((id) =>
      assetMapping.value[id]?.trim(),
    ),
);
function message(reason: unknown) {
  return reason instanceof Error ? reason.message : "操作暂时无法完成。";
}
async function load() {
  loading.value = true;
  error.value = "";
  try {
    packages.value = await listPackages();
  } catch (reason) {
    error.value = message(reason);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
async function choose(item: CatalogPackage) {
  selected.value = item;
  screenName.value = `${item.name} 副本`;
  datasetMapping.value = {};
  assetMapping.value = {};
  error.value = "";
  if (
    item.kind === "template" &&
    (item.manifest.datasets.length || item.manifest.assets.length)
  ) {
    try {
      const [ds, as] = await Promise.all([
        listDatasets(),
        listAssets({ limit: 100 }),
      ]);
      datasets.value = ds;
      assets.value = as;
    } catch (reason) {
      error.value = message(reason);
    }
  }
}
function selectFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] ?? null;
}
async function install() {
  if (!file.value || !trusted.value || busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    const installed = await installPackage(file.value);
    await load();
    await choose(installed);
    trusted.value = false;
    file.value = null;
  } catch (reason) {
    error.value = message(reason);
  } finally {
    busy.value = false;
  }
}
async function remove() {
  if (!selected.value || busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    await uninstallPackage(selected.value);
    selected.value = null;
    await load();
  } catch (reason) {
    error.value = message(reason);
  } finally {
    busy.value = false;
  }
}
async function apply() {
  if (!selected.value || !applyReady.value || busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    const created = await applyTemplate(selected.value, {
      name: screenName.value.trim(),
      dataset_mapping: { ...datasetMapping.value },
      asset_mapping: { ...assetMapping.value },
    });
    await router.push({ name: "screen-edit", params: { id: created.id } });
  } catch (reason) {
    error.value = message(reason);
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <section class="catalog-page" aria-label="模板与插件目录">
    <header>
      <p class="page-eyebrow">本实例目录</p>
      <h1>模板与插件</h1>
      <p>导入离线包，复用大屏模板与组件。每个版本独立保存。</p>
    </header>
    <p v-if="error" class="catalog-error" role="alert">{{ error }}</p>
    <form v-if="canAdmin" class="catalog-import" @submit.prevent="install">
      <label
        >离线安装包
        <input
          type="file"
          accept=".zip,application/zip"
          :disabled="busy"
          @change="selectFile"
      /></label>
      <label class="catalog-trust"
        ><input
          v-model="trusted"
          type="checkbox"
        />我已核实来源。插件将在同源页面执行受信任代码，错误隔离不提供恶意代码沙箱。</label
      >
      <button
        class="primary-button"
        data-action="install-package"
        type="submit"
        :disabled="busy || !file || !trusted"
      >
        {{ busy ? "处理中…" : "导入安装包" }}
      </button>
    </form>
    <div class="catalog-filters">
      <input
        v-model="filter"
        aria-label="搜索安装包"
        placeholder="搜索模板、组件、包标识"
      /><select v-model="kind" aria-label="安装包类型">
        <option value="all">全部类型</option>
        <option value="template">模板</option>
        <option value="plugin">组件插件</option>
      </select>
    </div>
    <p v-if="loading" role="status">正在加载目录…</p>
    <p v-else-if="!visible.length">目录中暂无匹配的安装包。</p>
    <div class="catalog-layout">
      <div class="catalog-list">
        <button
          v-for="item in visible"
          :key="`${item.kind}/${item.id}@${item.version}`"
          class="catalog-card"
          type="button"
          :data-package="`${item.id}@${item.version}`"
          :aria-pressed="
            selected?.id === item.id && selected?.version === item.version
          "
          @click="choose(item)"
        >
          <span
            >{{ item.kind === "template" ? "大屏模板" : "组件插件" }} ·
            {{ item.version }}</span
          ><strong>{{ item.name }}</strong>
          <p>{{ item.description || item.id }}</p>
          <small>{{ item.license }} · {{ item.source }}</small>
        </button>
      </div>
      <aside v-if="selected" class="catalog-detail" aria-label="安装包详情">
        <h2>{{ selected.name }}</h2>
        <p>{{ selected.description }}</p>
        <dl>
          <dt>标识</dt>
          <dd>{{ selected.id }}</dd>
          <dt>版本</dt>
          <dd>{{ selected.version }}</dd>
          <dt>许可证</dt>
          <dd>{{ selected.license }}</dd>
          <dt>来源</dt>
          <dd>{{ selected.source }}</dd>
          <dt>API 兼容性</dt>
          <dd>{{ selected.compatible_api }}</dd>
          <dt>安装时间</dt>
          <dd>{{ new Date(selected.installed_at).toLocaleString() }}</dd>
        </dl>
        <details>
          <summary>包校验信息</summary>
          <code>{{ selected.sha256 }}</code>
          <p>{{ selected.files.length }} 个文件</p>
        </details>
        <template v-if="selected.kind === 'plugin'"
          ><h3>组件</h3>
          <p
            v-for="component in selected.manifest.components"
            :key="component.type"
          >
            {{ component.name }} <small>{{ component.type }}</small>
          </p>
          <p>
            进入大屏编辑器，从“已安装插件”添加组件。已发布大屏继续使用原版本。
          </p></template
        >
        <form v-else-if="canCreate" @submit.prevent="apply">
          <h3>创建大屏草稿</h3>
          <label
            >大屏名称<input v-model="screenName" name="screen-name" required
          /></label>
          <label
            v-for="reference in selected.manifest.datasets"
            :key="reference"
            >数据集：{{ reference
            }}<input
              v-model="datasetMapping[reference]"
              list="catalog-datasets"
              required
              placeholder="选择本实例数据集 ID"
          /></label>
          <datalist id="catalog-datasets">
            <option
              v-for="dataset in datasets"
              :key="dataset.id"
              :value="dataset.id"
            >
              {{ dataset.name }}
            </option>
          </datalist>
          <label v-for="reference in selected.manifest.assets" :key="reference"
            >资产：{{ reference
            }}<input
              v-model="assetMapping[reference]"
              list="catalog-assets"
              required
              placeholder="选择本实例资产 ID"
          /></label>
          <datalist id="catalog-assets">
            <option v-for="asset in assets" :key="asset.id" :value="asset.id">
              {{ asset.name }}
            </option>
          </datalist>
          <p>应用后进入草稿编辑器，完成检查后再发布。</p>
          <button
            class="primary-button"
            type="button"
            data-action="apply-template"
            :disabled="busy || !applyReady"
            @click="apply"
          >
            使用模板
          </button>
        </form>
        <button
          v-if="canAdmin"
          class="secondary-button"
          type="button"
          :disabled="busy"
          @click="remove"
        >
          卸载此版本
        </button>
        <p v-if="canAdmin" class="catalog-note">
          草稿或已发布大屏引用的插件版本不能卸载。
        </p>
      </aside>
    </div>
  </section>
</template>
<style scoped>
.catalog-page {
  display: grid;
  gap: 22px;
  max-width: 1280px;
}
.catalog-page h1,
.catalog-page h2,
.catalog-page p {
  margin: 0;
}
.catalog-page header {
  display: grid;
  gap: 8px;
}
.catalog-page header > p:last-child,
.catalog-note {
  color: var(--text-muted, #85888f);
}
.catalog-import {
  padding: 18px;
  border: 1px solid var(--border-color, #dedede);
  border-radius: 10px;
  display: grid;
  gap: 14px;
}
.catalog-import label {
  display: flex;
  align-items: center;
  gap: 10px;
}
.catalog-trust {
  font-size: 13px;
  line-height: 1.6;
}
.catalog-filters {
  display: flex;
  gap: 12px;
}
.catalog-filters input {
  flex: 1;
}
.catalog-layout {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(320px, 1fr);
  gap: 22px;
  align-items: start;
}
.catalog-list {
  display: grid;
  gap: 12px;
}
.catalog-card {
  text-align: left;
  background: transparent;
  color: inherit;
  border: 1px solid var(--border-color, #dedede);
  border-radius: 10px;
  display: grid;
  gap: 9px;
  padding: 18px;
  cursor: pointer;
}
.catalog-card[aria-pressed="true"] {
  border-color: #3b82f6;
}
.catalog-card > span,
.catalog-card > small {
  font-size: 12px;
  color: var(--text-muted, #85888f);
}
.catalog-card strong {
  font-size: 17px;
}
.catalog-card p {
  font-size: 13px;
  line-height: 1.6;
}
.catalog-detail {
  padding: 22px;
  border: 1px solid var(--border-color, #dedede);
  border-radius: 10px;
  display: grid;
  gap: 16px;
}
.catalog-detail dl {
  display: grid;
  grid-template-columns: 90px 1fr;
  gap: 10px;
  font-size: 13px;
  margin: 0;
}
.catalog-detail dd {
  margin: 0;
  overflow-wrap: anywhere;
}
.catalog-detail dt {
  color: var(--text-muted, #85888f);
}
.catalog-detail code {
  overflow-wrap: anywhere;
  font-size: 11px;
}
.catalog-detail form,
.catalog-detail form label {
  display: grid;
  gap: 10px;
}
.catalog-detail form p,
.catalog-note {
  font-size: 12px;
  line-height: 1.6;
}
.catalog-error {
  color: #dc2626;
}
.catalog-detail h3 {
  margin: 0;
  font-size: 14px;
}
.catalog-detail input,
.catalog-filters input,
.catalog-filters select {
  padding: 8px 10px;
  border: 1px solid var(--border-color, #bbb);
  border-radius: 6px;
  color: inherit;
  background: transparent;
}
.catalog-detail small {
  display: block;
  font-size: 11px;
  opacity: 0.7;
}
@media (max-width: 900px) {
  .catalog-layout {
    grid-template-columns: 1fr;
  }
}
</style>
