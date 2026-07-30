<script setup lang="ts">
defineProps<{
  name: "overview" | "datasources" | "datasets" | "screens" | "settings";
}>();
</script>

<template>
  <svg
    class="icon-glyph"
    viewBox="0 0 20 20"
    fill="none"
    stroke="currentColor"
    stroke-width="1.5"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <template v-if="name === 'overview'">
      <rect x="3" y="3" width="5" height="5" rx="1" />
      <rect x="12" y="3" width="5" height="5" rx="1" />
      <rect x="3" y="12" width="5" height="5" rx="1" />
      <rect x="12" y="12" width="5" height="5" rx="1" />
    </template>
    <template v-else-if="name === 'datasources'">
      <ellipse cx="10" cy="5" rx="6.5" ry="2.5" />
      <path d="M3.5 5v5c0 1.4 2.9 2.5 6.5 2.5s6.5-1.1 6.5-2.5V5" />
      <path d="M3.5 10v5c0 1.4 2.9 2.5 6.5 2.5s6.5-1.1 6.5-2.5v-5" />
    </template>
    <template v-else-if="name === 'datasets'">
      <path d="M4 3.5h8l4 4V16a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 4 16V3.5Z" />
      <path d="M12 3.5V8h4M7 11h6M7 14h5" />
    </template>
    <template v-else-if="name === 'screens'">
      <rect x="2.5" y="3.5" width="15" height="11" rx="1.5" />
      <path d="M7 17h6M10 14.5V17M5.5 11l2.7-2.8 2.2 2.1 3.8-4" />
    </template>
    <template v-else>
      <circle cx="10" cy="10" r="2.5" />
      <path d="M10 2.5v2M10 15.5v2M17.5 10h-2M4.5 10h-2M15.3 4.7l-1.4 1.4M6.1 13.9l-1.4 1.4M15.3 15.3l-1.4-1.4M6.1 6.1 4.7 4.7" />
    </template>
  </svg>
</template>
