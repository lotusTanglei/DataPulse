<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

import {
  createSqlEditor,
  type SqlEditorAdapter,
} from "./editorAdapter";
import type { SqlDialect } from "./types";

const props = defineProps<{
  modelValue: string;
  dialect: SqlDialect;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string];
  run: [];
}>();

const host = ref<HTMLElement | null>(null);
let adapter: SqlEditorAdapter | null = null;

onMounted(() => {
  if (host.value === null) {
    return;
  }
  adapter = createSqlEditor({
    parent: host.value,
    initialValue: props.modelValue,
    dialect: props.dialect,
    onChange: (value) => emit("update:modelValue", value),
    onRun: () => emit("run"),
  });
});

watch(
  () => props.modelValue,
  (value) => adapter?.setValue(value),
);

watch(
  () => props.dialect,
  (dialect) => adapter?.setDialect(dialect),
);

onBeforeUnmount(() => adapter?.destroy());
</script>

<template>
  <div ref="host" class="sql-editor" data-sql-editor />
</template>
