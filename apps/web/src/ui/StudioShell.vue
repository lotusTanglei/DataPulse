<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";

import { useAuthStore } from "../stores/auth";
import IconGlyph from "./IconGlyph.vue";

const route = useRoute();
const auth = useAuthStore();

const title = computed(() => String(route.meta.title ?? "DataPulse"));
const username = computed(() =>
  auth.state.status === "authenticated" ? auth.state.username : "admin",
);

const navigation = [
  { label: "概览", to: "/studio/overview", icon: "overview" as const },
  { label: "数据源", to: "/studio/datasources", icon: "datasources" as const },
  { label: "数据集", to: "/studio/datasets", icon: "datasets" as const },
  { label: "大屏", to: "/studio/screens", icon: "screens" as const },
];
</script>

<template>
  <div class="studio-frame">
    <aside class="studio-sidebar">
      <div class="workspace-switcher" aria-label="工作区导航">
        <span class="workspace-mark" aria-hidden="true">D</span>
        <span class="workspace-name">DataPulse</span>
        <span class="workspace-chevron" aria-hidden="true">⌄</span>
      </div>

      <nav class="sidebar-nav" aria-label="主导航">
        <RouterLink
          v-for="item in navigation"
          :key="item.to"
          :to="item.to"
          class="sidebar-link"
        >
          <IconGlyph :name="item.icon" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <section class="recent-section" aria-label="最近访问">
        <p class="sidebar-caption">最近访问</p>
        <p class="recent-empty">暂无最近项目</p>
      </section>

      <div class="sidebar-spacer" />

      <RouterLink to="/studio/settings" class="sidebar-link">
        <IconGlyph name="settings" />
        <span>系统设置</span>
      </RouterLink>
      <div class="account-row">
        <span class="account-avatar" aria-hidden="true">
          {{ username.slice(0, 1).toUpperCase() }}
        </span>
        <span class="account-name">{{ username }}</span>
      </div>
    </aside>

    <main class="studio-main">
      <header class="studio-topbar">
        <nav class="breadcrumb" aria-label="面包屑">
          <span>DataPulse</span>
          <span aria-hidden="true">/</span>
          <strong>{{ title }}</strong>
        </nav>
        <span class="environment-badge">本地工作区</span>
      </header>
      <div class="studio-content">
        <RouterView />
      </div>
    </main>
  </div>
</template>
