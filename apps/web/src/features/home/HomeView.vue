<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();
const title = computed(() => String(route.meta.title ?? "工作区"));
const description = computed(() => String(route.meta.description ?? ""));
</script>

<template>
  <section class="page-column" :aria-labelledby="`page-${String(route.name)}`">
    <p class="page-eyebrow">Workspace</p>
    <h1 :id="`page-${String(route.name)}`">{{ title }}</h1>
    <p class="page-description">{{ description }}</p>
    <div class="empty-panel">
      <div class="empty-panel__icon" aria-hidden="true">＋</div>
      <h2>{{ title }}工作区已就绪</h2>
      <p>下一步将在这里接入完整的管理与编辑能力。</p>
    </div>
  </section>
</template>
