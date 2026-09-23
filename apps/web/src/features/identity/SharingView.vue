<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ApiError, apiRequest } from "../../lib/api";
import InlineNotice from "../../ui/InlineNotice.vue";
import { getResourceAccess, listDirectory, listGrants, revokeGrant, saveGrant, type ResourceGrant, type ResourceType } from "./api";

const route = useRoute();
const types: Record<ResourceType, { label: string; endpoint: string }> = {
  screen: { label: "大屏", endpoint: "screens" }, datasource: { label: "数据源", endpoint: "datasources" },
  dataset: { label: "数据集", endpoint: "datasets" }, file: { label: "数据文件", endpoint: "files" }, asset: { label: "媒体资源", endpoint: "assets" },
};
const initialType = String(route.query.type ?? "screen") as ResourceType;
const resourceType = ref<ResourceType>(initialType in types ? initialType : "screen");
const resourceId = ref(String(route.query.id ?? ""));
const resources = ref<{ id: string; name?: string; original_name?: string }[]>([]);
const users = ref<{ id: string; username: string }[]>([]);
const grants = ref<ResourceGrant[]>([]);
const userId = ref("");
const permission = ref<ResourceGrant["permission"]>("read");
const loading = ref(false);
const busy = ref(false);
const error = ref("");
const notice = ref("");
const canManage = ref(false);
const accessChecked = ref(false);
let generation = 0;
let grantGeneration = 0;
const names = computed(() => new Map(users.value.map((user) => [user.id, user.username])));
const labels = { read: "可查看", write: "可编辑", publish: "可发布" };
function describe(value: unknown): string {
  return value instanceof ApiError ? `${value.message} (${value.code})` : "读取授权失败，请稍后重试。";
}
async function loadResources(): Promise<void> {
  const current = ++generation;
  loading.value = true;
  error.value = "";
  try {
    const value = await apiRequest<typeof resources.value>(`/api/admin/${types[resourceType.value].endpoint}`);
    if (current === generation) resources.value = value;
  } catch (value) { if (current === generation) error.value = describe(value); }
  finally { if (current === generation) loading.value = false; }
}
async function loadGrants(): Promise<void> {
  const current = ++grantGeneration;
  grants.value = [];
  canManage.value = false;
  accessChecked.value = false;
  error.value = "";
  if (!resourceId.value) return;
  try {
    const access = await getResourceAccess(resourceType.value, resourceId.value);
    if (current !== grantGeneration) return;
    canManage.value = access.manage;
    accessChecked.value = true;
    if (!access.manage) return;
    const result = await listGrants(resourceType.value, resourceId.value);
    if (current === grantGeneration) grants.value = result;
  } catch (value) { if (current === grantGeneration) error.value = describe(value); }
}
async function save(): Promise<void> {
  if (!canManage.value || busy.value || !resourceId.value || !userId.value) return;
  busy.value = true;
  error.value = notice.value = "";
  try {
    await saveGrant({ resource_type: resourceType.value, resource_id: resourceId.value, user_id: userId.value, permission: permission.value });
    notice.value = "共享授权已保存。数据集和媒体依赖需要分别授权。";
    await loadGrants();
  } catch (value) { error.value = describe(value); }
  finally { busy.value = false; }
}
async function revoke(grant: ResourceGrant): Promise<void> {
  if (!canManage.value || busy.value || !window.confirm("撤销后，对方后续访问将被拒绝。确认撤销？")) return;
  busy.value = true;
  try { await revokeGrant(grant); await loadGrants(); notice.value = "共享授权已撤销。"; }
  catch (value) { error.value = describe(value); }
  finally { busy.value = false; }
}
watch(resourceType, () => { resourceId.value = ""; permission.value = "read"; resources.value = []; void loadResources(); });
watch(resourceId, () => { void loadGrants(); });
onMounted(async () => {
  await loadResources();
  try { users.value = await listDirectory(); }
  catch (value) { error.value = describe(value); }
  if (resourceId.value) await loadGrants();
});
onBeforeUnmount(() => { generation++; grantGeneration++; });
</script>

<template>
  <section class="identity-page">
    <header class="page-header"><div><p class="page-eyebrow">团队协作</p><h1>资源共享</h1><p>拥有者和管理员可管理共享。只读用户始终只有查看权限；数据集和媒体依赖需单独授权。</p></div></header>
    <InlineNotice v-if="error" tone="error">{{ error }}</InlineNotice>
    <InlineNotice v-if="notice" tone="info">{{ notice }}</InlineNotice>
    <form class="identity-card identity-form" aria-label="共享资源" @submit.prevent="save">
      <label>资源类型<select aria-label="资源类型" v-model="resourceType" name="resource-type" :disabled="busy"><option v-for="(type, key) in types" :key="key" :value="key">{{ type.label }}</option></select></label>
      <label>资源<select aria-label="资源" v-model="resourceId" name="resource" required :disabled="loading || busy"><option value="">{{ loading ? "正在加载…" : "请选择资源" }}</option><option v-for="resource in resources" :key="resource.id" :value="resource.id">{{ resource.name || resource.original_name || resource.id }}</option></select></label>
      <p v-if="!loading && !resources.length">暂无可见资源。创建资源或请拥有者授予访问权限。</p>
      <p v-if="resourceId && accessChecked && !canManage">仅拥有者和管理员可以管理此资源的共享。请联系资源拥有者调整授权。</p>
      <template v-if="canManage">
        <label>共享给<select aria-label="共享给" v-model="userId" name="recipient" required :disabled="busy"><option value="">请选择用户</option><option v-for="user in users" :key="user.id" :value="user.id">{{ user.username }}</option></select></label>
        <label>权限<select aria-label="权限" v-model="permission" name="permission" :disabled="busy"><option value="read">可查看</option><option value="write">可编辑</option><option v-if="resourceType === 'screen'" value="publish">可发布</option></select></label>
        <button class="primary-button" :disabled="busy || !resourceId || !userId">{{ busy ? "正在保存…" : "保存共享授权" }}</button>
      </template>
    </form>
    <section v-if="resourceId && canManage" class="identity-card" aria-label="当前共享授权"><h2>当前共享授权</h2><p v-if="!grants.length">暂无共享授权。</p>
      <div v-else class="identity-table-wrap"><table class="identity-table"><thead><tr><th>用户</th><th>权限</th><th>操作</th></tr></thead><tbody><tr v-for="grant in grants" :key="grant.user_id"><td>{{ names.get(grant.user_id) ?? "已停用用户" }}</td><td>{{ labels[grant.permission] }}</td><td><button class="secondary-button" :disabled="busy" :aria-label="`撤销授权：${names.get(grant.user_id) ?? grant.user_id}`" @click="revoke(grant)">撤销</button></td></tr></tbody></table></div>
    </section>
  </section>
</template>

<style src="./identity.css"></style>
