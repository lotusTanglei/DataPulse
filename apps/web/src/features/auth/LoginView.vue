<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";

import { ApiError } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import FormField from "../../ui/FormField.vue";
import InlineNotice from "../../ui/InlineNotice.vue";

const auth = useAuthStore();
const router = useRouter();
const username = ref("");
const password = ref("");
const submitting = ref(false);
const notice = ref("");
const serverFields = ref<Record<string, string>>({});

async function submit(): Promise<void> {
  notice.value = "";
  serverFields.value = {};
  submitting.value = true;
  try {
    await auth.login({
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
      notice.value = "登录失败，请稍后重试。";
    }
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <main class="auth-layout">
    <section class="auth-card auth-card--login" aria-labelledby="login-title">
      <div class="auth-brand">
        <span class="workspace-mark" aria-hidden="true">D</span>
        <span>DataPulse</span>
      </div>
      <div class="auth-heading">
        <p class="page-eyebrow">管理员登录</p>
        <h1 id="login-title">欢迎回来</h1>
        <p>登录后继续配置数据源、数据集和可视化大屏。</p>
      </div>

      <InlineNotice v-if="notice" tone="error">{{ notice }}</InlineNotice>

      <form class="auth-form" @submit.prevent="submit">
        <FormField
          label="用户名"
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
            autofocus
          />
        </FormField>
        <FormField
          label="密码"
          name="password"
          :error="serverFields.password"
          required
        >
          <input
            id="password"
            v-model="password"
            name="password"
            type="password"
            autocomplete="current-password"
            required
          />
        </FormField>
        <button class="primary-button" type="submit" :disabled="submitting">
          {{ submitting ? "正在登录…" : "登录" }}
        </button>
      </form>
      <p class="auth-footnote">编辑端仅允许管理员访问；发布页面的权限由宿主系统控制。</p>
    </section>
  </main>
</template>
