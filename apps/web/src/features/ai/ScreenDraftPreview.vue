<script setup lang="ts">
import type { DashboardDocument } from "../../contracts";
import { loadPreviewAsset } from "../player/api";
import ScreenRuntime from "../runtime/ScreenRuntime.vue";
import type { QueryComponent } from "../runtime/types";
import { queryScreenDocument } from "../screens/api";

const props = defineProps<{
  document: DashboardDocument;
}>();

const queryComponent: QueryComponent = (
  componentId,
  parameters,
  signal,
) => queryScreenDocument(props.document, componentId, parameters, signal);
</script>

<template>
  <div class="screen-draft-preview" aria-label="AI 大屏草稿预览">
    <ScreenRuntime
      :document="document"
      :load-asset="loadPreviewAsset"
      mode="preview"
      :query-component="queryComponent"
    />
  </div>
</template>

<style scoped>
.screen-draft-preview {
  width: 100%;
  height: min(420px, 42vh);
  min-height: 240px;
  overflow: hidden;
  border: 1px solid rgb(148 163 184 / 18%);
  border-radius: 12px;
  background: #080d16;
}
</style>
