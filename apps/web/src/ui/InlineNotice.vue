<script setup lang="ts">
withDefaults(
  defineProps<{
    tone?: "error" | "info";
  }>(),
  { tone: "info" },
);
</script>

<template>
  <div class="inline-notice" :data-tone="tone" :role="tone === 'error' ? 'alert' : 'status'">
    <span class="inline-notice__icon" aria-hidden="true">
      {{ tone === "error" ? "!" : "i" }}
    </span>
    <div><slot /></div>
  </div>
</template>
