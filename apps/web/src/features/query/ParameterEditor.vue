<script setup lang="ts">
import { Plus, Trash2 } from "@lucide/vue";
import { computed, reactive, watch } from "vue";

import type {
  JsonValue,
  ParameterDataType,
  QueryParameterInput,
} from "./types";

const props = withDefaults(
  defineProps<{
    modelValue: QueryParameterInput[];
    allowAdd?: boolean;
  }>(),
  { allowAdd: true },
);

const emit = defineEmits<{
  "update:modelValue": [rows: QueryParameterInput[]];
  validity: [valid: boolean];
}>();

const rawValues = reactive<Record<number, string>>({});
const valueErrors = reactive<Record<number, string>>({});

const nameErrors = computed(() => {
  const errors: Record<number, string> = {};
  const counts = new Map<string, number>();
  for (const row of props.modelValue) {
    const name = row.name.trim();
    counts.set(name, (counts.get(name) ?? 0) + 1);
  }
  props.modelValue.forEach((row, index) => {
    const name = row.name.trim();
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(name)) {
      errors[index] = "参数名需以字母或下划线开头";
    } else if ((counts.get(name) ?? 0) > 1) {
      errors[index] = "参数名不能重复";
    }
  });
  return errors;
});

const valid = computed(
  () =>
    Object.keys(nameErrors.value).length === 0 &&
    Object.keys(valueErrors).length === 0,
);

watch(
  () => props.modelValue,
  (rows) => {
    rows.forEach((row, index) => {
      if (!(index in rawValues)) {
        rawValues[index] = JSON.stringify(row.value);
      }
    });
    for (const index of Object.keys(rawValues).map(Number)) {
      if (index >= rows.length) {
        delete rawValues[index];
        delete valueErrors[index];
      }
    }
  },
  { immediate: true, deep: true },
);

watch(valid, (value) => emit("validity", value), { immediate: true });

function replace(index: number, patch: Partial<QueryParameterInput>): void {
  const rows = props.modelValue.map((row, rowIndex) =>
    rowIndex === index ? { ...row, ...patch } : row,
  );
  emit("update:modelValue", rows);
}

function updateValue(index: number, text: string): void {
  rawValues[index] = text;
  try {
    const value = JSON.parse(text) as JsonValue;
    delete valueErrors[index];
    replace(index, { value });
  } catch {
    valueErrors[index] = "请输入有效的 JSON 值";
  }
}

function add(): void {
  emit("update:modelValue", [
    ...props.modelValue,
    { name: "", data_type: "string", value: null },
  ]);
}

function remove(index: number): void {
  emit(
    "update:modelValue",
    props.modelValue.filter((_, rowIndex) => rowIndex !== index),
  );
  delete rawValues[index];
  delete valueErrors[index];
}

const dataTypes: Array<{ value: ParameterDataType; label: string }> = [
  { value: "string", label: "文本" },
  { value: "number", label: "数字" },
  { value: "integer", label: "整数" },
  { value: "boolean", label: "布尔" },
  { value: "date", label: "日期" },
  { value: "datetime", label: "日期时间" },
];
</script>

<template>
  <section class="parameter-editor" aria-label="查询参数">
    <div class="parameter-heading">
      <div>
        <h3>参数</h3>
        <p>值按 JSON 解析，并通过参数绑定传给数据库。</p>
      </div>
      <button
        v-if="allowAdd"
        class="quiet-button"
        type="button"
        @click="add"
      >
        <Plus :size="14" aria-hidden="true" />
        添加参数
      </button>
    </div>

    <p v-if="modelValue.length === 0" class="parameter-empty">
      当前查询没有参数。
    </p>

    <div
      v-for="(row, index) in modelValue"
      :key="index"
      class="parameter-row"
      :data-parameter-index="index"
    >
      <label>
        <span>名称</span>
        <input
          :name="`parameter-name.${index}`"
          :value="row.name"
          placeholder="region"
          @input="
            replace(index, {
              name: ($event.target as HTMLInputElement).value,
            })
          "
        />
        <small v-if="nameErrors[index]" class="field-error">
          {{ nameErrors[index] }}
        </small>
      </label>
      <label>
        <span>类型</span>
        <select
          :name="`parameter-type.${index}`"
          :value="row.data_type"
          @change="
            replace(index, {
              data_type: ($event.target as HTMLSelectElement)
                .value as ParameterDataType,
            })
          "
        >
          <option
            v-for="dataType in dataTypes"
            :key="dataType.value"
            :value="dataType.value"
          >
            {{ dataType.label }}
          </option>
        </select>
      </label>
      <label class="parameter-value">
        <span>值（JSON）</span>
        <input
          :name="`parameter.${row.name}`"
          :value="rawValues[index]"
          placeholder='例如 "north"'
          @input="
            updateValue(index, ($event.target as HTMLInputElement).value)
          "
        />
        <small v-if="valueErrors[index]" class="field-error">
          {{ valueErrors[index] }}
        </small>
      </label>
      <button
        v-if="allowAdd"
        class="icon-button"
        type="button"
        :aria-label="`删除参数 ${row.name || index + 1}`"
        @click="remove(index)"
      >
        <Trash2 :size="14" aria-hidden="true" />
      </button>
    </div>
  </section>
</template>
