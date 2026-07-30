<script setup lang="ts">
defineProps<{
  label: string;
  name: string;
  hint?: string;
  error?: string;
  required?: boolean;
}>();
</script>

<template>
  <div class="form-field" :data-invalid="Boolean(error)">
    <div class="form-field__heading">
      <label :for="name">{{ label }}</label>
      <span v-if="required" aria-hidden="true">*</span>
    </div>
    <slot />
    <p v-if="error" class="form-field__error">{{ error }}</p>
    <p v-else-if="hint" class="form-field__hint">{{ hint }}</p>
  </div>
</template>
