<script setup lang="ts">
import {
  Copy,
  LayoutDashboard,
  Plus,
  Trash2,
  X,
} from "@lucide/vue";
import { onBeforeUnmount, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { ApiError } from "../../lib/api";
import InlineNotice from "../../ui/InlineNotice.vue";
import {
  copyScreen,
  createScreen,
  deleteScreen,
  listScreens,
} from "./api";
import type { ScreenSummary } from "./types";

const router = useRouter();
const screens = ref<ScreenSummary[]>([]);
const loading = ref(true);
const error = ref<ApiError | null>(null);
const actionError = ref<ApiError | null>(null);
const actionId = ref<string | null>(null);
const createOpen = ref(false);
const createName = ref("");
const createError = ref("");
const creating = ref(false);
const controller = new AbortController();

const updatedAtFormatter = new Intl.DateTimeFormat("zh-CN", {
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

function fallbackError(
  reason: unknown,
  code: string,
  message: string,
): ApiError {
  return reason instanceof ApiError
    ? reason
    : new ApiError({
        code,
        message,
        requestId: "",
        status: 500,
      });
}

async function load(): Promise<void> {
  try {
    screens.value = await listScreens(controller.signal);
  } catch (reason) {
    if (!controller.signal.aborted) {
      error.value = fallbackError(
        reason,
        "SCREEN_LIST_FAILED",
        "暂时无法加载大屏。",
      );
    }
  } finally {
    if (!controller.signal.aborted) {
      loading.value = false;
    }
  }
}

function openCreate(): void {
  createName.value = "";
  createError.value = "";
  actionError.value = null;
  createOpen.value = true;
}

function closeCreate(): void {
  if (!creating.value) {
    createOpen.value = false;
  }
}

async function submitCreate(): Promise<void> {
  const name = createName.value.trim();
  if (!name) {
    createError.value = "请输入大屏名称";
    return;
  }
  creating.value = true;
  createError.value = "";
  try {
    const created = await createScreen({ name, description: "" });
    createOpen.value = false;
    await router.push(`/studio/screens/${created.id}/edit`);
  } catch (reason) {
    const apiError = fallbackError(
      reason,
      "SCREEN_CREATE_FAILED",
      "暂时无法创建大屏。",
    );
    createError.value = apiError.message;
  } finally {
    creating.value = false;
  }
}

async function copy(item: ScreenSummary): Promise<void> {
  if (actionId.value !== null) {
    return;
  }
  actionId.value = item.id;
  actionError.value = null;
  try {
    const copied = await copyScreen(item.id);
    screens.value = [...screens.value, copied];
  } catch (reason) {
    actionError.value = fallbackError(
      reason,
      "SCREEN_COPY_FAILED",
      "暂时无法复制大屏。",
    );
  } finally {
    actionId.value = null;
  }
}

async function remove(item: ScreenSummary): Promise<void> {
  if (
    actionId.value !== null ||
    !window.confirm(`删除“${item.name}”？此操作无法撤销。`)
  ) {
    return;
  }
  actionId.value = item.id;
  actionError.value = null;
  try {
    await deleteScreen(item.id);
    screens.value = screens.value.filter((screen) => screen.id !== item.id);
  } catch (reason) {
    actionError.value = fallbackError(
      reason,
      "SCREEN_DELETE_FAILED",
      "暂时无法删除大屏。",
    );
  } finally {
    actionId.value = null;
  }
}

function formatUpdatedAt(value: string): string {
  return updatedAtFormatter.format(new Date(value));
}

void load();
onBeforeUnmount(() => controller.abort());
</script>

<template>
  <section class="page-column screen-list-page" aria-labelledby="screen-list-title">
    <div class="page-heading">
      <div>
        <p class="page-eyebrow">可视化工作区</p>
        <h1 id="screen-list-title">大屏</h1>
        <p class="page-description">
          创建、调试并发布可独立播放或安全嵌入业务系统的数据大屏。
        </p>
      </div>
      <button
        class="primary-button primary-button--compact"
        type="button"
        data-action="open-create-screen"
        @click="openCreate"
      >
        <Plus :size="15" aria-hidden="true" />
        新建大屏
      </button>
    </div>

    <p v-if="loading" class="loading-copy" role="status">正在加载大屏…</p>
    <InlineNotice v-else-if="error" tone="error">
      <p>{{ error.message }}</p>
      <code v-if="error.requestId">{{ error.requestId }}</code>
    </InlineNotice>

    <template v-else>
      <InlineNotice v-if="actionError" tone="error">
        <p>{{ actionError.message }}</p>
        <code v-if="actionError.requestId">{{ actionError.requestId }}</code>
      </InlineNotice>

      <div v-if="screens.length === 0" class="empty-state screen-empty">
        <span class="empty-icon" aria-hidden="true">
          <LayoutDashboard :size="22" />
        </span>
        <h2>还没有大屏</h2>
        <p>从一张空白的 1920 × 1080 画布开始搭建。</p>
        <button
          class="secondary-button"
          type="button"
          data-action="open-create-screen"
          @click="openCreate"
        >
          <Plus :size="14" aria-hidden="true" />
          新建第一个大屏
        </button>
      </div>

      <div v-else class="screen-list" aria-label="大屏列表">
        <article v-for="item in screens" :key="item.id" class="screen-row">
          <RouterLink
            class="screen-row__main"
            :to="`/studio/screens/${item.id}/edit`"
          >
            <span class="screen-row__icon" aria-hidden="true">
              <LayoutDashboard :size="17" />
            </span>
            <span class="screen-row__copy">
              <span class="screen-row__title">
                <strong>{{ item.name }}</strong>
                <span
                  class="screen-status"
                  :data-published="item.published_at !== null"
                >
                  {{ item.published_at ? "已发布" : "草稿" }}
                </span>
              </span>
              <span class="screen-row__description">
                {{ item.description || "暂无描述" }}
              </span>
            </span>
            <span class="screen-row__updated">
              最后更新 {{ formatUpdatedAt(item.updated_at) }}
            </span>
          </RouterLink>

          <div class="screen-row__actions">
            <button
              class="screen-action"
              type="button"
              data-action="copy-screen"
              :aria-label="`复制大屏 ${item.name}`"
              :disabled="actionId !== null"
              @click="copy(item)"
            >
              <Copy :size="14" aria-hidden="true" />
              复制
            </button>
            <button
              class="screen-action screen-action--danger"
              type="button"
              data-action="delete-screen"
              :aria-label="`删除大屏 ${item.name}`"
              :disabled="actionId !== null"
              @click="remove(item)"
            >
              <Trash2 :size="14" aria-hidden="true" />
              删除
            </button>
          </div>
        </article>
      </div>
    </template>

    <div
      v-if="createOpen"
      class="dialog-backdrop"
      role="presentation"
      @mousedown.self="closeCreate"
    >
      <section
        class="dialog-card screen-create-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-screen-title"
      >
        <div class="dialog-heading">
          <div>
            <h2 id="create-screen-title">新建大屏</h2>
            <p>创建后将直接进入编辑器。</p>
          </div>
          <button
            class="dialog-close"
            type="button"
            aria-label="关闭"
            :disabled="creating"
            @click="closeCreate"
          >
            <X :size="16" aria-hidden="true" />
          </button>
        </div>
        <form class="dialog-form" @submit.prevent="submitCreate">
          <label
            class="form-field"
            :data-invalid="createError ? 'true' : 'false'"
          >
            <span class="form-field__heading">大屏名称</span>
            <input
              v-model="createName"
              name="screenName"
              autocomplete="off"
              autofocus
              placeholder="例如：运营总览"
              @input="createError = ''"
            />
            <span v-if="createError" class="form-field__error">
              {{ createError }}
            </span>
          </label>
          <div class="dialog-actions">
            <button
              class="secondary-button"
              type="button"
              :disabled="creating"
              @click="closeCreate"
            >
              取消
            </button>
            <button class="primary-button" type="submit" :disabled="creating">
              {{ creating ? "正在创建…" : "创建并编辑" }}
            </button>
          </div>
        </form>
      </section>
    </div>
  </section>
</template>
