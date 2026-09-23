<script setup lang="ts">
withDefaults(
  defineProps<{
    tone?: "error" | "info" | "warning";
  }>(),
  { tone: "info" },
);
</script>

<template>
  <div class="inline-notice" :data-tone="tone" :role="tone === 'error' || tone === 'warning' ? 'alert' : 'status'">
    <span class="inline-notice__icon" aria-hidden="true">
      {{ tone === "error" || tone === "warning" ? "!" : "i" }}
    </span>
    <div><slot /></div>
  </div>
</template>
