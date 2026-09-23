<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ApiError } from "../../lib/api";
import type { UserRole } from "../../stores/auth";
import InlineNotice from "../../ui/InlineNotice.vue";
import { createUser, listIdentityAudit, listUsers, updateUser, type IdentityAudit, type StudioUser } from "./api";

const users = ref<StudioUser[]>([]);
const audit = ref<IdentityAudit[]>([]);
const username = ref("");
const password = ref("");
const role = ref<UserRole>("viewer");
const loading = ref(true);
const busy = ref(false);
const error = ref("");
const notice = ref("");
const selected = ref<StudioUser | null>(null);
const editRole = ref<UserRole>("viewer");
const resetPassword = ref("");
const showAudit = ref(false);
const roleLabels = { admin: "管理员", editor: "编辑者", viewer: "只读用户" };

function describe(value: unknown): string {
  return value instanceof ApiError ? `${value.message} (${value.code})` : "请求失败，请稍后重试。";
}
async function load(): Promise<void> {
  loading.value = true;
  error.value = "";
  try { users.value = await listUsers(); }
  catch (value) { error.value = describe(value); }
  finally { loading.value = false; }
}
async function create(): Promise<void> {
  if (busy.value) return;
  busy.value = true;
  error.value = notice.value = "";
  try {
    await createUser({ username: username.value.trim(), password: password.value, role: role.value });
    username.value = "";
    notice.value = "用户已创建。请通过可信渠道交付初始密码。";
    await load();
  } catch (value) { error.value = describe(value); }
  finally { password.value = ""; busy.value = false; }
}
function edit(user: StudioUser): void {
  selected.value = user;
  editRole.value = user.role;
  resetPassword.value = "";
}
async function save(): Promise<void> {
  if (!selected.value || busy.value) return;
  if (!window.confirm("保存后，该用户已有会话将失效，需要重新登录。继续保存？")) return;
  busy.value = true;
  error.value = "";
  try {
    await updateUser(selected.value.id, {
      role: editRole.value,
      ...(resetPassword.value ? { password: resetPassword.value } : {}),
    });
    selected.value = null;
    notice.value = "账号已更新，原会话已撤销。";
    await load();
  } catch (value) { error.value = describe(value); }
  finally { resetPassword.value = ""; busy.value = false; }
}
async function toggle(user: StudioUser): Promise<void> {
  if (busy.value || !window.confirm(`${user.active ? "停用后会立即撤销会话。停用" : "启用"}用户“${user.username}”？`)) return;
  busy.value = true;
  error.value = "";
  try { await updateUser(user.id, { active: !user.active }); await load(); }
  catch (value) { error.value = describe(value); }
  finally { busy.value = false; }
}
async function loadAudit(): Promise<void> {
  error.value = "";
  try { audit.value = await listIdentityAudit(); showAudit.value = true; }
  catch (value) { error.value = describe(value); }
}
onMounted(load);
</script>

<template>
  <section class="identity-page">
    <header class="page-header"><div><p class="page-eyebrow">工作区管理</p><h1>用户管理</h1><p>管理登录账号和角色。资源通过共享授权，观看者的嵌入权限由宿主系统管理。</p></div></header>
    <InlineNotice v-if="error" tone="error">{{ error }}</InlineNotice>
    <InlineNotice v-if="notice" tone="info">{{ notice }}</InlineNotice>
    <form class="identity-card identity-form" aria-label="创建用户" @submit.prevent="create">
      <h2>创建用户</h2>
      <label>用户名<input v-model="username" name="username" autocomplete="off" maxlength="255" required /></label>
      <label>初始密码<input v-model="password" name="password" type="password" autocomplete="new-password" minlength="10" required /></label>
      <label>角色<select aria-label="角色" v-model="role" name="role"><option value="viewer">只读用户</option><option value="editor">编辑者</option><option value="admin">管理员</option></select></label>
      <button class="primary-button" :disabled="busy" type="submit">{{ busy ? "正在保存…" : "创建用户" }}</button>
    </form>
    <section class="identity-card" aria-label="用户列表">
      <div class="identity-actions"><h2>工作区用户</h2><button class="secondary-button" :disabled="loading || busy" @click="load">刷新</button></div>
      <p v-if="loading" role="status">正在加载用户…</p>
      <p v-else-if="!users.length">暂无用户。</p>
      <div v-else class="identity-table-wrap"><table class="identity-table"><thead><tr><th>用户名</th><th>角色</th><th>状态</th><th>操作</th></tr></thead><tbody>
        <tr v-for="user in users" :key="user.id"><td>{{ user.username }}</td><td>{{ roleLabels[user.role] }}</td><td>{{ user.active ? "启用" : "已停用" }}</td><td class="identity-actions">
          <button class="secondary-button" :disabled="busy" :aria-label="`编辑用户：${user.username}`" @click="edit(user)">角色与密码</button>
          <button class="secondary-button" :disabled="busy" :aria-label="`${user.active ? '停用' : '启用'}用户：${user.username}`" @click="toggle(user)">{{ user.active ? "停用" : "启用" }}</button>
        </td></tr>
      </tbody></table></div>
    </section>
    <form v-if="selected" class="identity-card identity-form" aria-label="编辑用户" @submit.prevent="save">
      <h2>编辑 {{ selected.username }}</h2>
      <label>角色<select aria-label="角色" v-model="editRole" name="edit-role"><option value="viewer">只读用户</option><option value="editor">编辑者</option><option value="admin">管理员</option></select></label>
      <label>重置密码（留空保留原密码）<input v-model="resetPassword" name="reset-password" type="password" autocomplete="new-password" minlength="10" /></label>
      <p>角色变更或密码重置会撤销该用户的已有会话。至少保留一位有效管理员。</p>
      <div class="identity-actions"><button class="primary-button" :disabled="busy">保存账号</button><button type="button" class="secondary-button" @click="selected = null; resetPassword = ''">取消</button></div>
    </form>
    <section class="identity-card"><div class="identity-actions"><h2>权限审计</h2><button class="secondary-button" @click="loadAudit">查看最近记录</button></div>
      <div v-if="showAudit" class="identity-table-wrap"><p v-if="!audit.length">暂无审计记录。</p><table v-else class="identity-table"><thead><tr><th>时间</th><th>动作</th><th>操作者</th><th>资源</th></tr></thead><tbody><tr v-for="event in audit" :key="event.id"><td>{{ event.created_at }}</td><td>{{ event.action }}</td><td>{{ event.actor_id }}</td><td>{{ event.resource_type }} / {{ event.resource_id }}</td></tr></tbody></table></div>
    </section>
  </section>
</template>

<style src="./identity.css"></style>
