<script setup lang="ts">
import { ChevronDown, ChevronRight, RefreshCw } from "@lucide/vue";
import { computed, onBeforeUnmount, watch, ref } from "vue";

import { ApiError } from "../../lib/api";
import {
  describeRelation,
  listNamespaces,
  listRelations,
  previewRelation,
} from "./api";
import type {
  Datasource,
  NamespaceInfo,
  RelationInfo,
  RelationSchema,
} from "./types";
import type { QueryResult } from "../query/types";

interface CollectionBranch<T> {
  items: T[];
  loading: boolean;
  error: string;
  requestId: string;
  loaded: boolean;
}

interface SchemaBranch {
  schema: RelationSchema | null;
  loading: boolean;
  error: string;
  requestId: string;
}

interface PreviewBranch {
  result: QueryResult | null;
  loading: boolean;
  error: string;
  requestId: string;
}

const props = defineProps<{ datasource: Datasource }>();
const namespaces = ref<CollectionBranch<NamespaceInfo>>(emptyCollection());
const relationBranches = ref<Record<string, CollectionBranch<RelationInfo>>>({});
const schemaBranches = ref<Record<string, SchemaBranch>>({});
const previewBranches = ref<Record<string, PreviewBranch>>({});
const expandedNamespaces = ref<Set<string>>(new Set());
const expandedRelations = ref<Set<string>>(new Set());
const controllers = new Map<string, AbortController>();

const isSQLite = computed(() => props.datasource.config.type === "sqlite");

function emptyCollection<T>(): CollectionBranch<T> {
  return {
    items: [],
    loading: false,
    error: "",
    requestId: "",
    loaded: false,
  };
}

function namespaceKey(namespace: string | null): string {
  return namespace ?? "";
}

function relationKey(namespace: string | null, relation: string): string {
  return `${props.datasource.id}::${namespaceKey(namespace)}::${relation}`;
}

function collectionKey(namespace: string | null): string {
  return `${props.datasource.id}::${namespaceKey(namespace)}`;
}

function relationBranch(namespace: string | null): CollectionBranch<RelationInfo> {
  return relationBranches.value[collectionKey(namespace)] ?? emptyCollection();
}

function schemaBranch(namespace: string | null, relation: string): SchemaBranch {
  return (
    schemaBranches.value[relationKey(namespace, relation)] ?? {
      schema: null,
      loading: false,
      error: "",
      requestId: "",
    }
  );
}

function previewBranch(namespace: string | null, relation: string): PreviewBranch {
  return (
    previewBranches.value[relationKey(namespace, relation)] ?? {
      result: null,
      loading: false,
      error: "",
      requestId: "",
    }
  );
}

function branchError(reason: unknown): { message: string; requestId: string } {
  if (reason instanceof ApiError) {
    return { message: reason.message, requestId: reason.requestId };
  }
  return { message: "无法读取 Schema，请稍后重试。", requestId: "" };
}

function controllerFor(key: string): AbortController {
  controllers.get(key)?.abort();
  const controller = new AbortController();
  controllers.set(key, controller);
  return controller;
}

function releaseController(key: string, controller: AbortController): void {
  if (controllers.get(key) === controller) {
    controllers.delete(key);
  }
}

async function loadNamespaceList(): Promise<void> {
  const key = `${props.datasource.id}::namespaces`;
  const controller = controllerFor(key);
  namespaces.value = {
    ...namespaces.value,
    loading: true,
    error: "",
    requestId: "",
  };
  try {
    const items = await listNamespaces(props.datasource.id, controller.signal);
    if (!controller.signal.aborted) {
      namespaces.value = {
        items,
        loading: false,
        error: "",
        requestId: "",
        loaded: true,
      };
    }
  } catch (reason) {
    if (!controller.signal.aborted) {
      const error = branchError(reason);
      namespaces.value = {
        items: [],
        loading: false,
        error: error.message,
        requestId: error.requestId,
        loaded: false,
      };
    }
  } finally {
    releaseController(key, controller);
  }
}

async function loadRelationList(
  namespace: string | null,
  force = false,
): Promise<void> {
  const key = collectionKey(namespace);
  const existing = relationBranches.value[key];
  if (!force && (existing?.loaded || existing?.loading)) {
    return;
  }
  const controller = controllerFor(key);
  relationBranches.value = {
    ...relationBranches.value,
    [key]: {
      items: force ? [] : (existing?.items ?? []),
      loading: true,
      error: "",
      requestId: "",
      loaded: false,
    },
  };
  try {
    const items = await listRelations(
      props.datasource.id,
      namespace,
      controller.signal,
    );
    if (!controller.signal.aborted) {
      relationBranches.value = {
        ...relationBranches.value,
        [key]: {
          items,
          loading: false,
          error: "",
          requestId: "",
          loaded: true,
        },
      };
    }
  } catch (reason) {
    if (!controller.signal.aborted) {
      const error = branchError(reason);
      relationBranches.value = {
        ...relationBranches.value,
        [key]: {
          items: [],
          loading: false,
          error: error.message,
          requestId: error.requestId,
          loaded: false,
        },
      };
    }
  } finally {
    releaseController(key, controller);
  }
}

async function loadRelationSchema(relation: RelationInfo): Promise<void> {
  const key = relationKey(relation.namespace, relation.name);
  const existing = schemaBranches.value[key];
  if (existing?.schema !== null && existing !== undefined) {
    return;
  }
  const controller = controllerFor(key);
  schemaBranches.value = {
    ...schemaBranches.value,
    [key]: {
      schema: null,
      loading: true,
      error: "",
      requestId: "",
    },
  };
  try {
    const schema = await describeRelation(
      props.datasource.id,
      relation.namespace,
      relation.name,
      controller.signal,
    );
    if (!controller.signal.aborted) {
      schemaBranches.value = {
        ...schemaBranches.value,
        [key]: {
          schema,
          loading: false,
          error: "",
          requestId: "",
        },
      };
    }
  } catch (reason) {
    if (!controller.signal.aborted) {
      const error = branchError(reason);
      schemaBranches.value = {
        ...schemaBranches.value,
        [key]: {
          schema: null,
          loading: false,
          error: error.message,
          requestId: error.requestId,
        },
      };
    }
  } finally {
    releaseController(key, controller);
  }
}

async function loadRelationPreview(relation: RelationInfo): Promise<void> {
  const key = `${relationKey(relation.namespace, relation.name)}::preview`;
  const branchKey = relationKey(relation.namespace, relation.name);
  const controller = controllerFor(key);
  previewBranches.value = {
    ...previewBranches.value,
    [branchKey]: {
      result: previewBranch(relation.namespace, relation.name).result,
      loading: true,
      error: "",
      requestId: "",
    },
  };
  try {
    const result = await previewRelation(
      props.datasource.id,
      relation.namespace,
      relation.name,
      100,
      controller.signal,
    );
    if (!controller.signal.aborted) {
      previewBranches.value = {
        ...previewBranches.value,
        [branchKey]: { result, loading: false, error: "", requestId: "" },
      };
    }
  } catch (reason) {
    if (!controller.signal.aborted) {
      const error = branchError(reason);
      previewBranches.value = {
        ...previewBranches.value,
        [branchKey]: {
          result: null,
          loading: false,
          error: error.message,
          requestId: error.requestId,
        },
      };
    }
  } finally {
    releaseController(key, controller);
  }
}

async function toggleNamespace(namespace: string): Promise<void> {
  const next = new Set(expandedNamespaces.value);
  if (next.has(namespace)) {
    next.delete(namespace);
    controllers.get(collectionKey(namespace))?.abort();
    for (const [key, controller] of controllers) {
      if (key.startsWith(`${props.datasource.id}::${namespace}::`)) {
        controller.abort();
      }
    }
  } else {
    next.add(namespace);
    void loadRelationList(namespace);
  }
  expandedNamespaces.value = next;
}

async function toggleRelation(relation: RelationInfo): Promise<void> {
  const key = relationKey(relation.namespace, relation.name);
  const next = new Set(expandedRelations.value);
  if (next.has(key)) {
    next.delete(key);
    controllers.get(key)?.abort();
  } else {
    next.add(key);
    void loadRelationSchema(relation);
  }
  expandedRelations.value = next;
}

async function refreshNamespace(namespace: string): Promise<void> {
  const prefix = `${props.datasource.id}::${namespace}::`;
  schemaBranches.value = Object.fromEntries(
    Object.entries(schemaBranches.value).filter(([key]) => !key.startsWith(prefix)),
  );
  expandedRelations.value = new Set(
    [...expandedRelations.value].filter((key) => !key.startsWith(prefix)),
  );
  await loadRelationList(namespace, true);
}

function abortAll(): void {
  for (const controller of controllers.values()) {
    controller.abort();
  }
  controllers.clear();
}

function reset(): void {
  abortAll();
  namespaces.value = emptyCollection();
  relationBranches.value = {};
  schemaBranches.value = {};
  previewBranches.value = {};
  expandedNamespaces.value = new Set();
  expandedRelations.value = new Set();
  if (isSQLite.value) {
    void loadRelationList(null);
  } else {
    void loadNamespaceList();
  }
}

watch(() => props.datasource.id, reset, { immediate: true });
onBeforeUnmount(abortAll);
</script>

<template>
  <div class="schema-browser">
    <div class="schema-toolbar">
      <div>
        <h2>Schema 浏览器</h2>
        <p>按需读取命名空间、关系和字段。</p>
      </div>
      <button
        v-if="!isSQLite"
        class="table-action"
        type="button"
        aria-label="刷新命名空间列表"
        @click="loadNamespaceList"
      >
        <RefreshCw :size="13" aria-hidden="true" />
        刷新
      </button>
    </div>

    <p v-if="namespaces.loading" class="catalog-loading" role="status">
      正在读取命名空间…
    </p>
    <div v-else-if="namespaces.error" class="catalog-error">
      <p>{{ namespaces.error }}</p>
      <code v-if="namespaces.requestId">{{ namespaces.requestId }}</code>
    </div>

    <div v-if="!isSQLite" class="catalog-tree">
      <div
        v-for="namespace in namespaces.items"
        :key="namespace.name ?? ''"
        class="catalog-namespace"
        :data-namespace="namespace.name ?? ''"
      >
        <div class="catalog-row">
          <button
            class="catalog-toggle"
            type="button"
            :aria-label="`${expandedNamespaces.has(namespace.name ?? '') ? '收起' : '展开'}命名空间 ${namespace.name ?? ''}`"
            :aria-expanded="expandedNamespaces.has(namespace.name ?? '')"
            @click="toggleNamespace(namespace.name ?? '')"
          >
            <ChevronDown
              v-if="expandedNamespaces.has(namespace.name ?? '')"
              :size="14"
              aria-hidden="true"
            />
            <ChevronRight v-else :size="14" aria-hidden="true" />
            <strong>{{ namespace.name }}</strong>
          </button>
          <button
            class="table-action"
            type="button"
            :aria-label="`刷新命名空间 ${namespace.name ?? ''}`"
            @click="refreshNamespace(namespace.name ?? '')"
          >
            <RefreshCw :size="12" aria-hidden="true" />
            刷新
          </button>
        </div>

        <div v-if="expandedNamespaces.has(namespace.name ?? '')" class="catalog-branch">
          <p
            v-if="relationBranch(namespace.name).loading"
            class="catalog-loading"
            role="status"
          >
            正在读取关系…
          </p>
          <div
            v-else-if="relationBranch(namespace.name).error"
            class="catalog-error"
          >
            <p>{{ relationBranch(namespace.name).error }}</p>
            <code v-if="relationBranch(namespace.name).requestId">
              {{ relationBranch(namespace.name).requestId }}
            </code>
          </div>
          <template
            v-for="relation in relationBranch(namespace.name).items"
            :key="relationKey(relation.namespace, relation.name)"
          >
            <div
              class="catalog-relation"
              :data-relation="`${namespace.name ?? ''}.${relation.name}`"
            >
              <button
                class="catalog-toggle"
                type="button"
                :aria-label="`${expandedRelations.has(relationKey(relation.namespace, relation.name)) ? '收起' : '展开'}关系 ${relation.name}`"
                :aria-expanded="expandedRelations.has(relationKey(relation.namespace, relation.name))"
                @click="toggleRelation(relation)"
              >
                <ChevronDown
                  v-if="
                    expandedRelations.has(
                      relationKey(relation.namespace, relation.name),
                    )
                  "
                  :size="14"
                  aria-hidden="true"
                />
                <ChevronRight v-else :size="14" aria-hidden="true" />
                <span>{{ relation.name }}</span>
                <small>{{ relation.kind === "view" ? "视图" : "表" }}</small>
              </button>
              <div
                v-if="
                  expandedRelations.has(
                    relationKey(relation.namespace, relation.name),
                  )
                "
                class="catalog-fields"
              >
                <p
                  v-if="schemaBranch(relation.namespace, relation.name).loading"
                  class="catalog-loading"
                >
                  正在读取字段…
                </p>
                <div
                  v-else-if="schemaBranch(relation.namespace, relation.name).error"
                  class="catalog-error"
                >
                  {{ schemaBranch(relation.namespace, relation.name).error }}
                </div>
                <div
                  v-for="field in schemaBranch(relation.namespace, relation.name)
                    .schema?.fields ?? []"
                  :key="field.name"
                  class="catalog-field"
                  :data-field-name="field.name"
                >
                  <span>{{ field.name }}</span>
                  <code>{{ field.data_type }}</code>
                  <small>{{ field.nullable ? "可空" : "必填" }}</small>
                </div>
                <button
                  class="table-action"
                  type="button"
                  :data-preview-relation="relation.name"
                  :disabled="previewBranch(relation.namespace, relation.name).loading"
                  @click="loadRelationPreview(relation)"
                >
                  {{
                    previewBranch(relation.namespace, relation.name).loading
                      ? "正在读取数据…"
                      : "预览数据（最多 100 行）"
                  }}
                </button>
                <div
                  v-if="previewBranch(relation.namespace, relation.name).error"
                  class="catalog-error"
                >
                  <p>{{ previewBranch(relation.namespace, relation.name).error }}</p>
                  <code
                    v-if="previewBranch(relation.namespace, relation.name).requestId"
                  >
                    {{ previewBranch(relation.namespace, relation.name).requestId }}
                  </code>
                </div>
                <div
                  v-if="previewBranch(relation.namespace, relation.name).result"
                  class="catalog-preview"
                  :data-preview-table="relation.name"
                >
                  <table>
                    <thead>
                      <tr>
                        <th
                          v-for="column in previewBranch(relation.namespace, relation.name).result?.columns"
                          :key="column.name"
                        >
                          {{ column.name }}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="(row, rowIndex) in previewBranch(relation.namespace, relation.name).result?.rows"
                        :key="rowIndex"
                      >
                        <td v-for="(value, valueIndex) in row" :key="valueIndex">
                          {{ value === null ? "—" : String(value) }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                  <small v-if="previewBranch(relation.namespace, relation.name).result?.row_count === 0">
                    暂无数据
                  </small>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>

    <div v-else class="catalog-tree catalog-tree--sqlite">
      <p v-if="relationBranch(null).loading" class="catalog-loading" role="status">
        正在读取关系…
      </p>
      <div v-else-if="relationBranch(null).error" class="catalog-error">
        <p>{{ relationBranch(null).error }}</p>
        <code v-if="relationBranch(null).requestId">
          {{ relationBranch(null).requestId }}
        </code>
      </div>
      <div
        v-for="relation in relationBranch(null).items"
        :key="relationKey(null, relation.name)"
        class="catalog-relation"
        :data-relation="`.${relation.name}`"
      >
        <button
          class="catalog-toggle"
          type="button"
          :aria-label="`${expandedRelations.has(relationKey(null, relation.name)) ? '收起' : '展开'}关系 ${relation.name}`"
          :aria-expanded="expandedRelations.has(relationKey(null, relation.name))"
          @click="toggleRelation(relation)"
        >
          <ChevronDown
            v-if="expandedRelations.has(relationKey(null, relation.name))"
            :size="14"
            aria-hidden="true"
          />
          <ChevronRight v-else :size="14" aria-hidden="true" />
          <span>{{ relation.name }}</span>
          <small>{{ relation.kind === "view" ? "视图" : "表" }}</small>
        </button>
        <div
          v-if="expandedRelations.has(relationKey(null, relation.name))"
          class="catalog-fields"
        >
          <p
            v-if="schemaBranch(null, relation.name).loading"
            class="catalog-loading"
          >
            正在读取字段…
          </p>
          <div
            v-else-if="schemaBranch(null, relation.name).error"
            class="catalog-error"
          >
            {{ schemaBranch(null, relation.name).error }}
          </div>
          <div
            v-for="field in schemaBranch(null, relation.name).schema?.fields ?? []"
            :key="field.name"
            class="catalog-field"
            :data-field-name="field.name"
          >
            <span>{{ field.name }}</span>
            <code>{{ field.data_type }}</code>
            <small>{{ field.nullable ? "可空" : "必填" }}</small>
          </div>
          <button
            class="table-action"
            type="button"
            :data-preview-relation="relation.name"
            :disabled="previewBranch(null, relation.name).loading"
            @click="loadRelationPreview(relation)"
          >
            {{
              previewBranch(null, relation.name).loading
                ? "正在读取数据…"
                : "预览数据（最多 100 行）"
            }}
          </button>
          <div
            v-if="previewBranch(null, relation.name).error"
            class="catalog-error"
          >
            <p>{{ previewBranch(null, relation.name).error }}</p>
            <code v-if="previewBranch(null, relation.name).requestId">
              {{ previewBranch(null, relation.name).requestId }}
            </code>
          </div>
          <div
            v-if="previewBranch(null, relation.name).result"
            class="catalog-preview"
            :data-preview-table="relation.name"
          >
            <table>
              <thead>
                <tr>
                  <th
                    v-for="column in previewBranch(null, relation.name).result?.columns"
                    :key="column.name"
                  >
                    {{ column.name }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(row, rowIndex) in previewBranch(null, relation.name).result?.rows"
                  :key="rowIndex"
                >
                  <td v-for="(value, valueIndex) in row" :key="valueIndex">
                    {{ value === null ? "—" : String(value) }}
                  </td>
                </tr>
              </tbody>
            </table>
            <small v-if="previewBranch(null, relation.name).result?.row_count === 0">
              暂无数据
            </small>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
