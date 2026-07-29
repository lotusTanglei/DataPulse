<script setup lang="ts">
import { onMounted, ref } from "vue";

import { getHealth } from "./lib/api";

type ServerState =
  | { status: "checking" }
  | { status: "available"; version: string }
  | { status: "unavailable" };

const server = ref<ServerState>({ status: "checking" });

onMounted(async () => {
  try {
    const health = await getHealth();
    server.value = { status: "available", version: health.version };
  } catch {
    server.value = { status: "unavailable" };
  }
});
</script>

<template>
  <main class="shell">
    <section class="hero" aria-labelledby="product-title">
      <p class="eyebrow">AI-native data storytelling</p>
      <h1 id="product-title">DataPulse</h1>
      <p class="vision">
        可私有化部署、可嵌入其他系统的数据分析与大屏创作平台。
      </p>
      <p class="server-status" :data-state="server.status" aria-live="polite">
        <template v-if="server.status === 'checking'">Checking server</template>
        <template v-else-if="server.status === 'available'">
          Server {{ server.version }}
        </template>
        <template v-else>Server unavailable</template>
      </p>
    </section>
  </main>
</template>
