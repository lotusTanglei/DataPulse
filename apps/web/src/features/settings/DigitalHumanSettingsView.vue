<script setup lang="ts">
import {
  Check,
  Pencil,
  PlugZap,
  RefreshCw,
  Save,
  Trash2,
  Volume2,
} from "@lucide/vue";
import { onMounted, reactive, ref } from "vue";

import { ApiError } from "../../lib/api";
import InlineNotice from "../../ui/InlineNotice.vue";
import { listExpiringAssets, type ScreenAsset } from "../screens/assets/api";
import {
  createDigitalHumanProvider,
  clearDigitalHumanCache,
  deleteDigitalHumanProvider,
  getDigitalHumanSettings,
  getDigitalHumanCostReport,
  getDigitalHumanMetrics,
  getDigitalHumanUsage,
  listDigitalHumanProviderHealth,
  listDigitalHumanAudit,
  listDigitalHumanTasks,
  retryDigitalHumanTask,
  listDigitalHumanProviders,
  listDigitalHumanVoices,
  testDigitalHumanProvider,
  updateDigitalHumanProvider,
  updateDigitalHumanSettings,
} from "./api";
import type {
  DigitalHumanProvider,
  DigitalHumanAudit,
  DigitalHumanProviderCreate,
  DigitalHumanCostReport,
  DigitalHumanMetrics,
  DigitalHumanProviderHealth,
  DigitalHumanProviderPatch,
  DigitalHumanSettings,
  DigitalHumanSettingsPatch,
  DigitalHumanUsage,
  ProviderType,
  SpeechTask,
  SpeechTaskStatus,
} from "./types";

const settings = ref<DigitalHumanSettings | null>(null);
const providers = ref<DigitalHumanProvider[]>([]);
const usage = ref<DigitalHumanUsage | null>(null);
const costReport = ref<DigitalHumanCostReport | null>(null);
const metrics = ref<DigitalHumanMetrics | null>(null);
const healthHistory = ref<Record<string, DigitalHumanProviderHealth[]>>({});
const tasks = ref<SpeechTask[]>([]);
const audit = ref<DigitalHumanAudit[]>([]);
const expiringAssets = ref<ScreenAsset[]>([]);
const loading = ref(true);
const saving = ref(false);
const refreshing = ref(false);
const creating = ref(false);
const error = ref<ApiError | null>(null);
const notice = ref("");
const clearingCache = ref(false);
const providerError = ref("");
const testing = ref<Set<string>>(new Set());
const deleting = ref<Set<string>>(new Set());
const loadingVoices = ref<Set<string>>(new Set());
const retryingTasks = ref<Set<string>>(new Set());
const voices = ref<Record<string, string[]>>({});
const editingProviderId = ref<string | null>(null);

const draft = reactive<Required<DigitalHumanSettingsPatch>>({
  enabled: true,
  default_muted: false,
  default_subtitles: true,
  max_speech_seconds: 30,
  cooldown_seconds: 5,
  daily_task_limit: 1000,
  daily_audio_seconds_limit: 36000,
  ai_enabled: true,
  ai_model: "",
  ai_context_limit: 100,
  data_retention_days: 30,
  forbidden_words: [],
  sensitive_patterns: [],
  manual_review_required: false,
});

const providerForm = reactive<DigitalHumanProviderCreate>({
  name: "",
  provider_type: "openai_compatible",
  base_url: "",
  api_key: "",
  default_voice: "alloy",
  language: "zh-CN",
  enabled: true,
  cost_per_minute: 0,
  provider_version: "v1",
});

const providerTypeLabels: Record<ProviderType, string> = {
  openai_compatible: "OpenAI-compatible",
  azure: "Azure",
  custom: "自定义",
};
const taskStatusLabels: Record<SpeechTaskStatus, string> = {
  queued: "排队中",
  running: "执行中",
  succeeded: "成功",
  failed: "失败",
  cancelled: "已取消",
};

function copySettings(value: DigitalHumanSettings): void {
  settings.value = value;
  draft.enabled = value.enabled;
  draft.default_muted = value.default_muted;
  draft.default_subtitles = value.default_subtitles;
  draft.max_speech_seconds = value.max_speech_seconds;
  draft.cooldown_seconds = value.cooldown_seconds;
  draft.daily_task_limit = value.daily_task_limit;
  draft.daily_audio_seconds_limit = value.daily_audio_seconds_limit;
  draft.ai_enabled = value.ai_enabled;
  draft.ai_model = value.ai_model;
  draft.ai_context_limit = value.ai_context_limit;
  draft.data_retention_days = value.data_retention_days;
  draft.forbidden_words = [...(value.forbidden_words ?? [])];
  draft.sensitive_patterns = [...(value.sensitive_patterns ?? [])];
  draft.manual_review_required = value.manual_review_required ?? false;
}

function parseLines(value: string): string[] {
  return value.split("\n").map((item) => item.trim()).filter(Boolean);
}

function errorMessage(reason: unknown, fallback: string): string {
  return reason instanceof ApiError ? reason.message : fallback;
}

async function load(): Promise<void> {
  loading.value = true;
  error.value = null;
  try {
    const [nextSettings, nextProviders, nextUsage, nextMetrics, nextCostReport, nextTasks, nextAudit] = await Promise.all([
      getDigitalHumanSettings(),
      listDigitalHumanProviders(),
      getDigitalHumanUsage(),
      getDigitalHumanMetrics(),
      getDigitalHumanCostReport(),
      listDigitalHumanTasks(),
      listDigitalHumanAudit(),
    ]);
    copySettings(nextSettings);
    providers.value = nextProviders;
    usage.value = nextUsage;
    metrics.value = nextMetrics;
    costReport.value = nextCostReport;
    tasks.value = nextTasks;
    audit.value = nextAudit;
    await loadHealth(nextProviders);
    await loadExpiringAssets();
  } catch (reason) {
    error.value =
      reason instanceof ApiError
        ? reason
        : new ApiError({
            code: "DIGITAL_HUMAN_SETTINGS_LOAD_FAILED",
            message: "暂时无法加载数字人设置。",
            requestId: "",
            status: 500,
          });
  } finally {
    loading.value = false;
  }
}

async function refresh(): Promise<void> {
  if (refreshing.value) return;
  refreshing.value = true;
  notice.value = "";
  try {
    const [nextProviders, nextUsage, nextMetrics, nextCostReport, nextTasks, nextAudit] = await Promise.all([
      listDigitalHumanProviders(),
      getDigitalHumanUsage(),
      getDigitalHumanMetrics(),
      getDigitalHumanCostReport(),
      listDigitalHumanTasks(),
      listDigitalHumanAudit(),
    ]);
    providers.value = nextProviders;
    usage.value = nextUsage;
    metrics.value = nextMetrics;
    costReport.value = nextCostReport;
    tasks.value = nextTasks;
    audit.value = nextAudit;
    await loadHealth(nextProviders);
    await loadExpiringAssets();
    notice.value = "状态已刷新。";
  } catch (reason) {
    error.value = new ApiError({
      code: "DIGITAL_HUMAN_REFRESH_FAILED",
      message: errorMessage(reason, "刷新数字人状态失败。"),
      requestId: reason instanceof ApiError ? reason.requestId : "",
      status: reason instanceof ApiError ? reason.status : 500,
    });
  } finally {
    refreshing.value = false;
  }
}

async function loadHealth(nextProviders: DigitalHumanProvider[]): Promise<void> {
  const entries = await Promise.all(
    nextProviders.map(async (provider) => {
      try {
        return [provider.id, await listDigitalHumanProviderHealth(provider.id)] as const;
      } catch {
        return [provider.id, []] as const;
      }
    }),
  );
  healthHistory.value = Object.fromEntries(entries);
}

async function loadExpiringAssets(): Promise<void> {
  try {
    expiringAssets.value = await listExpiringAssets(30);
  } catch {
    expiringAssets.value = [];
  }
}

async function saveSettings(): Promise<void> {
  if (saving.value) return;
  saving.value = true;
  notice.value = "";
  error.value = null;
  try {
    const updated = await updateDigitalHumanSettings({ ...draft });
    copySettings(updated);
    notice.value = "数字人设置已保存。";
  } catch (reason) {
    error.value = new ApiError({
      code: "DIGITAL_HUMAN_SETTINGS_SAVE_FAILED",
      message: errorMessage(reason, "保存数字人设置失败。"),
      requestId: reason instanceof ApiError ? reason.requestId : "",
      status: reason instanceof ApiError ? reason.status : 500,
    });
  } finally {
    saving.value = false;
  }
}

async function clearCache(): Promise<void> {
  if (clearingCache.value || !window.confirm("清空未被大屏引用的语音缓存？已发布资源不会被删除。")) return;
  clearingCache.value = true;
  error.value = null;
  try {
    const result = await clearDigitalHumanCache();
    notice.value = `已解除 ${result.detached_task_count} 条缓存任务，删除 ${result.deleted_asset_count} 个未引用音频资源。`;
    await refresh();
  } catch (reason) {
    error.value = new ApiError({
      code: "DIGITAL_HUMAN_CACHE_CLEAR_FAILED",
      message: errorMessage(reason, "清空语音缓存失败。"),
      requestId: reason instanceof ApiError ? reason.requestId : "",
      status: reason instanceof ApiError ? reason.status : 500,
    });
  } finally {
    clearingCache.value = false;
  }
}

async function retryTask(task: SpeechTask): Promise<void> {
  if (retryingTasks.value.has(task.id) || task.status !== "failed") return;
  retryingTasks.value = new Set(retryingTasks.value).add(task.id);
  try {
    const retried = await retryDigitalHumanTask(task.plan_id);
    tasks.value = [retried, ...tasks.value.filter((item) => item.id !== task.id)];
    notice.value = "任务已重新入队，服务端治理策略仍会生效。";
  } catch (reason) {
    error.value = new ApiError({
      code: "DIGITAL_HUMAN_TASK_RETRY_FAILED",
      message: errorMessage(reason, "任务重试失败。"),
      requestId: reason instanceof ApiError ? reason.requestId : "",
      status: reason instanceof ApiError ? reason.status : 500,
    });
  } finally {
    const next = new Set(retryingTasks.value);
    next.delete(task.id);
    retryingTasks.value = next;
  }
}

function editProvider(provider: DigitalHumanProvider): void {
  editingProviderId.value = provider.id;
  providerForm.name = provider.name;
  providerForm.provider_type = provider.provider_type;
  providerForm.base_url = provider.base_url;
  providerForm.api_key = "";
  providerForm.default_voice = provider.default_voice;
  providerForm.language = provider.language;
  providerForm.enabled = provider.enabled;
  providerForm.cost_per_minute = provider.cost_per_minute;
  providerForm.provider_version = provider.provider_version;
  providerError.value = "";
}

function cancelProviderEdit(): void {
  editingProviderId.value = null;
  providerForm.name = "";
  providerForm.base_url = "";
  providerForm.api_key = "";
  providerForm.default_voice = "alloy";
  providerForm.language = "zh-CN";
  providerForm.enabled = true;
  providerForm.cost_per_minute = 0;
  providerForm.provider_version = "v1";
}

async function saveProvider(): Promise<void> {
  if (creating.value || !providerForm.name.trim()) {
    providerError.value = "请填写供应商名称。";
    return;
  }
  creating.value = true;
  providerError.value = "";
  try {
    const payload: DigitalHumanProviderPatch = {
      ...providerForm,
      name: providerForm.name.trim(),
      base_url: providerForm.base_url.trim(),
      api_key: providerForm.api_key?.trim() || undefined,
    };
    if (editingProviderId.value) {
      const updated = await updateDigitalHumanProvider(editingProviderId.value, payload);
      providers.value = providers.value.map((item) => item.id === updated.id ? updated : item);
      notice.value = `供应商“${updated.name}”已更新。`;
    } else {
      const created = await createDigitalHumanProvider(payload as DigitalHumanProviderCreate);
      providers.value = [...providers.value, created].sort((a, b) => a.name.localeCompare(b.name, "zh-CN"));
      notice.value = `供应商“${created.name}”已添加。`;
    }
    cancelProviderEdit();
  } catch (reason) {
    providerError.value = errorMessage(reason, "添加供应商失败。支持的密钥只会发送一次。 ");
  } finally {
    creating.value = false;
  }
}

async function loadVoices(provider: DigitalHumanProvider): Promise<void> {
  if (loadingVoices.value.has(provider.id)) return;
  loadingVoices.value = new Set(loadingVoices.value).add(provider.id);
  providerError.value = "";
  try {
    voices.value = { ...voices.value, [provider.id]: await listDigitalHumanVoices(provider.id) };
  } catch (reason) {
    providerError.value = errorMessage(reason, "语音列表加载失败。");
  } finally {
    const next = new Set(loadingVoices.value);
    next.delete(provider.id);
    loadingVoices.value = next;
  }
}

async function testProvider(provider: DigitalHumanProvider): Promise<void> {
  if (testing.value.has(provider.id)) return;
  testing.value = new Set(testing.value).add(provider.id);
  providerError.value = "";
  try {
    const result = await testDigitalHumanProvider(provider.id);
    notice.value = result.ok
      ? `“${provider.name}”连接正常，延迟 ${result.latency_ms} ms。`
      : `“${provider.name}”检查失败：${result.error_code ?? "未知错误"}。`;
  } catch (reason) {
    providerError.value = errorMessage(reason, "供应商连接测试失败。");
  } finally {
    const next = new Set(testing.value);
    next.delete(provider.id);
    testing.value = next;
  }
}

async function removeProvider(provider: DigitalHumanProvider): Promise<void> {
  if (deleting.value.has(provider.id)) return;
  if (!window.confirm(`删除供应商“${provider.name}”？已有任务不会被删除。`)) return;
  deleting.value = new Set(deleting.value).add(provider.id);
  providerError.value = "";
  try {
    await deleteDigitalHumanProvider(provider.id);
    providers.value = providers.value.filter((item) => item.id !== provider.id);
    const nextVoices = { ...voices.value };
    delete nextVoices[provider.id];
    voices.value = nextVoices;
    notice.value = `供应商“${provider.name}”已删除。`;
  } catch (reason) {
    providerError.value = errorMessage(reason, "删除供应商失败。");
  } finally {
    const next = new Set(deleting.value);
    next.delete(provider.id);
    deleting.value = next;
  }
}

function formatDate(value: string | null): string {
  return value
    ? new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(
        new Date(value),
      )
    : "尚未检查";
}

function taskDate(task: SpeechTask): string {
  return formatDate(task.finished_at ?? task.started_at ?? task.created_at);
}

const healthStatusLabels: Record<DigitalHumanProvider["health_status"], string> = {
  unconfigured: "未配置",
  disabled: "已停用",
  healthy: "健康",
  degraded: "降级",
  open: "熔断",
};

function formatCost(value: number): string {
  return new Intl.NumberFormat("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value);
}

function auditDate(entry: DigitalHumanAudit): string {
  return formatDate(entry.created_at);
}

onMounted(load);
</script>

<template>
  <section class="page-column digital-human-settings" aria-labelledby="digital-human-settings-title">
    <div class="page-heading-row">
      <div>
        <p class="page-eyebrow">Runtime governance</p>
        <h1 id="digital-human-settings-title">数字人设置</h1>
        <p class="page-description">控制播报开关、供应商、限额和运行状态。</p>
      </div>
      <button class="secondary-button" type="button" :disabled="refreshing" @click="refresh">
        <RefreshCw :size="15" aria-hidden="true" :class="{ 'is-spinning': refreshing }" />
        刷新状态
      </button>
    </div>

    <p v-if="loading" class="loading-copy" role="status">正在加载数字人设置…</p>
    <InlineNotice v-else-if="error" tone="error">
      <p>{{ error.message }}</p>
      <code v-if="error.requestId">{{ error.requestId }}</code>
    </InlineNotice>

    <template v-else>
      <InlineNotice v-if="notice" tone="info"><p>{{ notice }}</p></InlineNotice>

      <form class="settings-section" aria-labelledby="runtime-settings-title" @submit.prevent="saveSettings">
        <div class="settings-section__heading">
          <div>
            <h2 id="runtime-settings-title">运行策略</h2>
            <p>这些限制由服务端执行，适用于所有大屏和嵌入播放。</p>
          </div>
          <button class="primary-button primary-button--compact" type="submit" :disabled="saving">
            <Save :size="14" aria-hidden="true" />
            {{ saving ? "保存中…" : "保存设置" }}
          </button>
        </div>
        <div class="settings-toggle-row">
          <label class="settings-toggle"><input v-model="draft.enabled" type="checkbox" /><span><strong>启用数字人播报</strong><small>关闭后新任务会被服务端拒绝，已有资产仍可播放。</small></span></label>
          <label class="settings-toggle"><input v-model="draft.default_muted" type="checkbox" /><span><strong>默认静音</strong><small>新实例默认不输出声音，字幕仍可显示。</small></span></label>
          <label class="settings-toggle"><input v-model="draft.default_subtitles" type="checkbox" /><span><strong>默认显示字幕</strong><small>为没有独立字幕轨道的播报显示文本字幕。</small></span></label>
        </div>
        <div class="form-grid">
          <label class="form-field"><span>单条最长播报（秒）</span><input v-model.number="draft.max_speech_seconds" type="number" min="1" max="3600" step="1" /></label>
          <label class="form-field"><span>组件冷却时间（秒）</span><input v-model.number="draft.cooldown_seconds" type="number" min="0" max="86400" step="1" /></label>
          <label class="form-field"><span>每日任务数上限</span><input v-model.number="draft.daily_task_limit" type="number" min="1" max="1000000" step="1" /></label>
          <label class="form-field"><span>每日音频时长上限（秒）</span><input v-model.number="draft.daily_audio_seconds_limit" type="number" min="1" max="10000000" step="1" /></label>
        </div>
        <p v-if="settings" class="settings-meta">上次保存：{{ formatDate(settings.updated_at) }}</p>
      </form>

      <form class="settings-section" aria-labelledby="governance-settings-title" @submit.prevent="saveSettings">
        <div class="settings-section__heading"><div><h2 id="governance-settings-title">AI 与保留策略</h2><p>AI 只接收允许的变量名；服务端会定期清理超出保留期的播报诊断记录。</p></div><Check :size="20" aria-hidden="true" /></div>
        <div class="settings-toggle-row"><label class="settings-toggle"><input v-model="draft.ai_enabled" type="checkbox" /><span><strong>启用 AI 话术预览</strong><small>关闭后不会向 AI 网关发送数字人话术请求。</small></span></label><label class="settings-toggle"><input v-model="draft.manual_review_required" type="checkbox" /><span><strong>播报前需要人工审核</strong><small>任务必须由管理端显式确认后才会入队。</small></span></label></div>
        <div class="form-grid"><label class="form-field"><span>AI 模型（留空使用网关默认）</span><input v-model="draft.ai_model" autocomplete="off" /></label><label class="form-field"><span>允许变量上限</span><input v-model.number="draft.ai_context_limit" type="number" min="1" max="10000" step="1" /></label><label class="form-field"><span>诊断数据保留天数</span><input v-model.number="draft.data_retention_days" type="number" min="1" max="3650" step="1" /></label></div>
        <div class="form-grid governance-inputs"><label class="form-field"><span>禁播词（每行一个）</span><textarea :value="draft.forbidden_words.join('\n')" rows="4" @input="draft.forbidden_words = parseLines(($event.target as HTMLTextAreaElement).value)" /></label><label class="form-field"><span>敏感信息正则（每行一个）</span><textarea :value="draft.sensitive_patterns.join('\n')" rows="4" @input="draft.sensitive_patterns = parseLines(($event.target as HTMLTextAreaElement).value)" /></label></div>
        <button class="secondary-button secondary-button--compact" type="submit" :disabled="saving"><Save :size="14" aria-hidden="true" />保存治理设置</button>
      </form>

      <section v-if="expiringAssets.length" class="settings-section" aria-labelledby="asset-expiry-title">
        <div class="settings-section__heading"><div><h2 id="asset-expiry-title">资源授权即将到期</h2><p>未来 30 天内到期的数字人资源需要续期或替换，已发布快照不会被自动删除。</p></div><Check :size="20" aria-hidden="true" /></div>
        <div class="notion-table-wrap provider-table-wrap"><table class="notion-table"><thead><tr><th>资源</th><th>类型</th><th>到期时间</th><th>上传者</th></tr></thead><tbody><tr v-for="asset in expiringAssets" :key="asset.id"><td><strong>{{ asset.name }}</strong><small class="provider-url">{{ asset.original_name }}</small></td><td>{{ asset.asset_type }}</td><td>{{ formatDate(asset.license_expires_at ?? null) }}</td><td>{{ asset.uploaded_by || "—" }}</td></tr></tbody></table></div>
      </section>

      <section class="settings-section" aria-labelledby="provider-settings-title">
        <div class="settings-section__heading"><div><h2 id="provider-settings-title">TTS 供应商</h2><p>密钥只在创建时发送并由服务端加密保存，列表不会回显。</p></div><Volume2 :size="20" aria-hidden="true" /></div>
        <div class="provider-create-grid">
          <label class="form-field"><span>名称</span><input v-model="providerForm.name" autocomplete="off" placeholder="例如：生产语音服务" /></label>
          <label class="form-field"><span>类型</span><select v-model="providerForm.provider_type"><option v-for="(label, type) in providerTypeLabels" :key="type" :value="type">{{ label }}</option></select></label>
          <label class="form-field"><span>Base URL</span><input v-model="providerForm.base_url" type="url" autocomplete="url" placeholder="https://tts.example.com" /></label>
          <label class="form-field"><span>API 密钥</span><input v-model="providerForm.api_key" type="password" autocomplete="new-password" placeholder="仅发送一次" /></label>
          <label class="form-field"><span>默认语音</span><input v-model="providerForm.default_voice" autocomplete="off" placeholder="alloy" /></label>
          <label class="form-field"><span>语言</span><input v-model="providerForm.language" autocomplete="off" placeholder="zh-CN" /></label>
          <label class="form-field"><span>估算单价（每分钟）</span><input v-model.number="providerForm.cost_per_minute" type="number" min="0" step="0.01" /></label>
          <label class="form-field"><span>供应商版本</span><input v-model="providerForm.provider_version" autocomplete="off" placeholder="v1" /></label>
          <div class="provider-form-actions"><button class="primary-button primary-button--compact provider-add" type="button" :disabled="creating" @click="saveProvider"><Save :size="14" aria-hidden="true" />{{ creating ? "保存中…" : editingProviderId ? "保存供应商" : "添加供应商" }}</button><button v-if="editingProviderId" class="secondary-button secondary-button--compact" type="button" @click="cancelProviderEdit">取消</button></div>
        </div>
        <p v-if="providerError" class="form-error" role="alert">{{ providerError }}</p>
        <div v-if="providers.length" class="notion-table-wrap provider-table-wrap">
          <table class="notion-table"><thead><tr><th>名称</th><th>类型</th><th>语言/语音</th><th>健康</th><th>配置/单价</th><th>最近检查</th><th class="notion-table__actions">操作</th></tr></thead><tbody>
            <tr v-for="provider in providers" :key="provider.id"><td><strong>{{ provider.name }}</strong><small class="provider-url">{{ provider.base_url || "未配置地址" }}</small></td><td>{{ providerTypeLabels[provider.provider_type] }}</td><td>{{ provider.language }} / {{ provider.default_voice || "未设置" }}<div v-if="voices[provider.id]?.length" class="voice-list"><span v-for="voice in voices[provider.id]" :key="voice">{{ voice }}</span></div></td><td><span class="status-copy" :data-status="provider.health_status === 'healthy' ? 'available' : provider.health_status === 'open' ? 'unavailable' : 'unknown'"><span class="status-dot" aria-hidden="true" />{{ healthStatusLabels[provider.health_status] }}</span><small v-if="provider.consecutive_failures">连续失败 {{ provider.consecutive_failures }} 次</small><small v-if="healthHistory[provider.id]?.length">历史检查 {{ healthHistory[provider.id].length }} 次</small></td><td><span class="status-copy" :data-status="provider.configured ? 'available' : 'unknown'"><span class="status-dot" aria-hidden="true" />{{ provider.configured ? "已配置" : "未配置" }}</span><small>每分钟 {{ formatCost(provider.cost_per_minute) }}</small></td><td>{{ formatDate(provider.last_checked_at) }}<small v-if="provider.last_latency_ms !== null">{{ provider.last_latency_ms }} ms</small></td><td class="notion-table__actions provider-actions"><button class="table-action" type="button" :disabled="testing.has(provider.id)" @click="testProvider(provider)"><PlugZap :size="13" aria-hidden="true" />{{ testing.has(provider.id) ? "测试中…" : "测试" }}</button><button class="table-action" type="button" :disabled="loadingVoices.has(provider.id)" @click="loadVoices(provider)"><Volume2 :size="13" aria-hidden="true" />{{ loadingVoices.has(provider.id) ? "加载中…" : "语音" }}</button><button class="icon-button" type="button" :aria-label="`编辑供应商：${provider.name}`" title="编辑供应商" @click="editProvider(provider)"><Pencil :size="14" aria-hidden="true" /></button><button class="icon-button icon-button--danger" type="button" :aria-label="`删除供应商：${provider.name}`" title="删除供应商" :disabled="deleting.has(provider.id)" @click="removeProvider(provider)"><Trash2 :size="14" aria-hidden="true" /></button></td></tr>
          </tbody></table>
        </div>
        <p v-else class="empty-inline">尚未配置 TTS 供应商。预录音频和浏览器语音不受影响。</p>
      </section>

      <section class="settings-section" aria-labelledby="usage-title">
        <div class="settings-section__heading"><div><h2 id="usage-title">今日用量</h2><p>任务成功、失败、取消和缓存命中都会进入服务端记录。</p></div><Check :size="20" aria-hidden="true" /></div>
        <div v-if="usage" class="usage-grid"><div><strong>{{ usage.task_count }}</strong><span>任务</span></div><div><strong>{{ usage.succeeded_count }}</strong><span>成功</span></div><div><strong>{{ usage.failed_count }}</strong><span>失败</span></div><div><strong>{{ Math.round(usage.generated_seconds) }}</strong><span>生成秒数</span></div><div><strong>{{ usage.cached_count }}</strong><span>缓存命中</span></div><div><strong>{{ formatCost(usage.estimated_cost) }}</strong><span>估算成本</span></div></div>
      </section>

      <section v-if="metrics" class="settings-section" aria-labelledby="metrics-title">
        <div class="settings-section__heading"><div><h2 id="metrics-title">运行指标</h2><p>任务、用量和合成耗时按当天持久聚合，不包含话术、查询结果或供应商凭据。</p></div><PlugZap :size="20" aria-hidden="true" /></div>
        <div class="usage-grid"><div><strong>{{ metrics.tasks_queued }}</strong><span>入队任务</span></div><div><strong>{{ metrics.tasks_succeeded }}</strong><span>成功任务</span></div><div><strong>{{ metrics.tasks_failed }}</strong><span>失败任务</span></div><div><strong>{{ metrics.tasks_cancelled }}</strong><span>取消任务</span></div><div><strong>{{ metrics.cache_hits }}</strong><span>缓存命中</span></div><div><strong>{{ Math.round(metrics.average_synthesis_ms) }}</strong><span>平均合成毫秒</span></div></div>
      </section>

      <section class="settings-section" aria-labelledby="cost-report-title">
        <div class="settings-section__heading"><div><h2 id="cost-report-title">成本估算</h2><p>按供应商汇总当前周期的生成时长和估算费用，实际账单以供应商为准。</p></div><div class="settings-section__heading-actions"><button class="secondary-button secondary-button--compact" type="button" :disabled="clearingCache" @click="clearCache"><Trash2 :size="14" aria-hidden="true" />{{ clearingCache ? "清理中…" : "清空未引用缓存" }}</button><Check :size="20" aria-hidden="true" /></div></div>
        <div v-if="costReport?.rows.length" class="notion-table-wrap provider-table-wrap"><table class="notion-table"><thead><tr><th>供应商</th><th>任务</th><th>生成时长</th><th>缓存命中</th><th>估算成本</th></tr></thead><tbody><tr v-for="row in costReport.rows" :key="row.provider_id"><td>{{ row.provider_name }}</td><td>{{ row.task_count }}</td><td>{{ Math.round(row.generated_seconds) }} 秒</td><td>{{ row.cached_count }}</td><td>{{ formatCost(row.estimated_cost) }}</td></tr></tbody><tfoot><tr><th>合计</th><th>{{ costReport.total_task_count }}</th><th>{{ Math.round(costReport.total_generated_seconds) }} 秒</th><th>—</th><th>{{ formatCost(costReport.total_estimated_cost) }}</th></tr></tfoot></table></div>
        <p v-else class="empty-inline">当前周期暂无成本记录。</p>
      </section>

      <section class="settings-section" aria-labelledby="diagnostics-title">
        <div class="settings-section__heading"><div><h2 id="diagnostics-title">最近播报任务</h2><p>显示最近 50 条任务，错误码可用于定位供应商或资源问题。</p></div><PlugZap :size="20" aria-hidden="true" /></div>
        <div v-if="tasks.length" class="notion-table-wrap provider-table-wrap"><table class="notion-table"><thead><tr><th>任务</th><th>状态</th><th>资产</th><th>错误</th><th>时间</th><th>操作</th></tr></thead><tbody><tr v-for="task in tasks" :key="task.id"><td><code>{{ task.id.slice(0, 8) }}</code></td><td><span class="status-copy" :data-status="task.status === 'succeeded' ? 'available' : task.status === 'failed' ? 'unavailable' : 'unknown'"><span class="status-dot" aria-hidden="true" />{{ taskStatusLabels[task.status] }}</span></td><td><code>{{ task.asset_id ? task.asset_id.slice(0, 8) : "—" }}</code></td><td>{{ task.error_code || "—" }}</td><td>{{ taskDate(task) }}</td><td><button v-if="task.status === 'failed'" class="table-action" type="button" :disabled="retryingTasks.has(task.id)" @click="retryTask(task)"><RefreshCw :size="13" aria-hidden="true" />{{ retryingTasks.has(task.id) ? "重试中…" : "重试" }}</button><span v-else>—</span></td></tr></tbody></table></div>
        <p v-else class="empty-inline">暂无播报任务记录。</p>
      </section>

      <section class="settings-section" aria-labelledby="audit-title">
        <div class="settings-section__heading"><div><h2 id="audit-title">治理审计</h2><p>仅显示稳定操作和错误元数据，不记录完整话术、查询结果或供应商密钥。</p></div><Check :size="20" aria-hidden="true" /></div>
        <div v-if="audit.length" class="notion-table-wrap provider-table-wrap"><table class="notion-table"><thead><tr><th>时间</th><th>操作</th><th>资源</th><th>详情</th></tr></thead><tbody><tr v-for="entry in audit" :key="entry.id"><td>{{ auditDate(entry) }}</td><td>{{ entry.action }}</td><td>{{ entry.resource_type }} / <code>{{ entry.resource_id.slice(0, 12) }}</code></td><td><code>{{ Object.entries(entry.details).map(([key, value]) => `${key}=${value}`).join(" · ") || "—" }}</code></td></tr></tbody></table></div>
        <p v-else class="empty-inline">暂无审计记录。</p>
      </section>
    </template>
  </section>
</template>

<style scoped>
.digital-human-settings { gap: 20px; }
.settings-section { padding: 20px 0; border-top: 1px solid var(--dp-border, #dfe5e8); }
.settings-section__heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 18px; }
.settings-section__heading h2 { margin: 0; color: var(--dp-text, #18232b); font-size: 18px; }
.settings-section__heading p { margin: 6px 0 0; color: var(--dp-muted, #64737d); font-size: 13px; }
.settings-section__heading > svg { color: var(--dp-accent, #1c8a78); }
.settings-section__heading-actions { display: flex; align-items: center; gap: 10px; }
.settings-toggle-row { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-bottom: 18px; }
.settings-toggle { display: flex; gap: 10px; align-items: flex-start; min-width: 0; padding: 12px; border: 1px solid var(--dp-border, #dfe5e8); border-radius: 6px; }
.settings-toggle input { width: 16px; height: 16px; margin: 2px 0 0; accent-color: var(--dp-accent, #1c8a78); }
.settings-toggle span { display: grid; gap: 4px; }
.settings-toggle strong { font-size: 13px; }
.settings-toggle small, .settings-meta, .provider-url { color: var(--dp-muted, #64737d); font-size: 12px; }
.settings-meta { margin: 14px 0 0; }
.provider-create-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; align-items: end; }
.provider-add { align-self: end; justify-self: start; }
.provider-form-actions { display: flex; align-items: center; gap: 8px; }
.form-error { margin: 12px 0; color: #b42318; font-size: 13px; }
.provider-table-wrap { margin-top: 18px; }
.provider-url { display: block; margin-top: 3px; max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.provider-actions { display: flex; gap: 8px; align-items: center; }
.voice-list { display: flex; flex-wrap: wrap; gap: 3px; margin-top: 4px; }
.voice-list span { padding: 2px 5px; border: 1px solid var(--dp-border, #dfe5e8); color: var(--dp-muted, #64737d); font-size: 10px; }
.icon-button--danger { color: #b42318; }
.empty-inline { margin: 18px 0 0; color: var(--dp-muted, #64737d); font-size: 13px; }
.usage-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 1px; border: 1px solid var(--dp-border, #dfe5e8); background: var(--dp-border, #dfe5e8); }
.usage-grid > div { display: grid; gap: 5px; padding: 16px; background: var(--dp-surface, #fff); }
.usage-grid strong { font-size: 24px; color: var(--dp-text, #18232b); }
.usage-grid span { color: var(--dp-muted, #64737d); font-size: 12px; }
.digital-human-settings code { font-size: 11px; }
.is-spinning { animation: spin 900ms linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (max-width: 900px) { .settings-toggle-row, .provider-create-grid { grid-template-columns: 1fr 1fr; } .usage-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 620px) { .settings-toggle-row, .provider-create-grid, .usage-grid { grid-template-columns: 1fr; } .settings-section__heading { flex-direction: column; } }
</style>
