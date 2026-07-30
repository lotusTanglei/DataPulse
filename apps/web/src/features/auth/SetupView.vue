<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";

import { ApiError } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import FormField from "../../ui/FormField.vue";
import InlineNotice from "../../ui/InlineNotice.vue";

const auth = useAuthStore();
const router = useRouter();
const code = ref("");
const username = ref("admin");
const password = ref("");
const passwordConfirmation = ref("");
const submitting = ref(false);
const notice = ref("");
const confirmationError = ref("");
const serverFields = ref<Record<string, string>>({});

async function submit(): Promise<void> {
  notice.value = "";
  confirmationError.value = "";
  serverFields.value = {};
  if (password.value !== passwordConfirmation.value) {
    confirmationError.value = "两次输入的密码不一致";
    return;
  }
  submitting.value = true;
  try {
    await auth.setup({
      code: code.value,
      username: username.value,
      password: password.value,
    });
    await router.replace("/studio/datasources");
  } catch (error) {
    if (error instanceof ApiError) {
      notice.value = error.message;
      serverFields.value = Object.fromEntries(
        error.fieldErrors.map((item) => [item.field, item.message]),
      );
    } else {
      notice.value = "初始化失败，请稍后重试。";
    }
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <main class="auth-layout">
    <section class="auth-card" aria-labelledby="setup-title">
      <div class="auth-brand">
        <span class="workspace-mark" aria-hidden="true">D</span>
        <span>DataPulse</span>
      </div>
      <div class="auth-heading">
        <p class="page-eyebrow">首次使用</p>
        <h1 id="setup-title">初始化 DataPulse</h1>
        <p>使用启动日志中的一次性初始化代码创建管理员账号。</p>
      </div>

      <InlineNotice v-if="notice" tone="error">{{ notice }}</InlineNotice>

      <form class="auth-form" @submit.prevent="submit">
        <FormField
          label="初始化代码"
          name="code"
          :error="serverFields.code"
          required
        >
          <input
            id="code"
            v-model="code"
            name="code"
            autocomplete="one-time-code"
            required
          />
        </FormField>
        <FormField
          label="管理员用户名"
          name="username"
          :error="serverFields.username"
          required
        >
          <input
            id="username"
            v-model="username"
            name="username"
            autocomplete="username"
            required
          />
        </FormField>
        <FormField
          label="密码"
          name="password"
          hint="至少 10 个字符"
          :error="serverFields.password"
          required
        >
          <input
            id="password"
            v-model="password"
            name="password"
            type="password"
            autocomplete="new-password"
            minlength="10"
            required
          />
        </FormField>
        <FormField
          label="确认密码"
          name="passwordConfirmation"
          :error="confirmationError"
          required
        >
          <input
            id="passwordConfirmation"
            v-model="passwordConfirmation"
            name="passwordConfirmation"
            type="password"
            autocomplete="new-password"
            minlength="10"
            required
          />
        </FormField>
        <button class="primary-button" type="submit" :disabled="submitting">
          {{ submitting ? "正在初始化…" : "创建管理员并进入工作区" }}
        </button>
      </form>
      <p class="auth-footnote">初始化代码仅可使用一次，完成后将自动失效。</p>
    </section>
  </main>
</template>
