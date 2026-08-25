<script setup lang="ts">
import { ref, watch } from "vue";

import { ApiError } from "../../lib/api";
import InlineNotice from "../../ui/InlineNotice.vue";
import type { ScreenAccessPolicy } from "./types";

const props = withDefaults(
  defineProps<{
    policy?: ScreenAccessPolicy;
    saving?: boolean;
    error?: ApiError | null;
  }>(),
  { policy: () => ({ allowed_origins: [], allowed_ips: [] }), saving: false, error: null },
);

const emit = defineEmits<{
  save: [policy: ScreenAccessPolicy];
}>();

const origins = ref("");
const ips = ref("");

function join(values: string[]): string {
  return values.join("\n");
}

watch(
  () => props.policy,
  (policy) => {
    origins.value = join(policy?.allowed_origins ?? []);
    ips.value = join(policy?.allowed_ips ?? []);
  },
  { immediate: true, deep: true },
);

function split(value: string): string[] {
  return [...new Set(value.split(/[\n,]+/).map((item) => item.trim()).filter(Boolean))];
}

function save(): void {
  emit("save", {
    allowed_origins: split(origins.value),
    allowed_ips: split(ips.value),
  });
}
</script>

<template>
  <section class="access-policy-panel" aria-label="访问限制">
    <header>
      <h2>访问限制</h2>
      <p>留空表示不限制。配置后，独立播放和嵌入都会按域名或 IP 校验。</p>
    </header>
    <InlineNotice v-if="error" tone="error">
      <p>{{ error.message }}</p>
      <code v-if="error.requestId">{{ error.requestId }}</code>
    </InlineNotice>
    <label class="policy-field">
      <span>允许的域名 / Origin</span>
      <textarea
        v-model="origins"
        rows="2"
        placeholder="https://dashboard.example.com"
        :disabled="saving"
      />
    </label>
    <label class="policy-field">
      <span>允许的 IP / CIDR</span>
      <textarea
        v-model="ips"
        rows="2"
        placeholder="192.0.2.10&#10;192.0.2.0/24"
        :disabled="saving"
      />
    </label>
    <button class="secondary-button" type="button" :disabled="saving" @click="save">
      {{ saving ? "保存中…" : "保存访问限制" }}
    </button>
  </section>
</template>

<style scoped>
.access-policy-panel {
  display: grid;
  gap: 10px;
  margin-top: 12px;
  padding: 16px;
  border: 1px solid rgb(148 163 184 / 22%);
  border-radius: 8px;
  background: rgb(15 23 42 / 28%);
}

.access-policy-panel h2,
.access-policy-panel p {
  margin: 0;
}

.access-policy-panel h2 {
  font-size: 15px;
}

.access-policy-panel p {
  margin-top: 5px;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.5;
}

.policy-field {
  display: grid;
  gap: 5px;
  color: #cbd5e1;
  font-size: 12px;
}

.policy-field textarea {
  width: 100%;
  min-height: 58px;
  resize: vertical;
}
</style>
