import type { DashboardDocument } from "../../../contracts";
import { defineStore } from "pinia";
import { computed, onScopeDispose, ref, toRaw } from "vue";

import { ApiError } from "../../../lib/api";
import type { AiEditCommand } from "../../ai/types";
import { getScreen, updateScreen } from "../api";
import type { Screen } from "../types";
import type { ChartSpec } from "../../../contracts";
import type { EditorCommand } from "./commands";
import { createSuggestedComponent } from "./chartSuggestion";
import { EditorHistory } from "./history";

export type SaveState =
  | "idle"
  | "dirty"
  | "saving"
  | "saved"
  | "failed"
  | "conflict";

export const useScreenEditorStore = defineStore("screen-editor", () => {
  const screen = ref<Screen | null>(null);
  const document = ref<DashboardDocument | null>(null);
  const selection = ref<string[]>([]);
  const saveState = ref<SaveState>("idle");
  const loadError = ref<ApiError | null>(null);
  const savingError = ref<ApiError | null>(null);
  const loading = ref(false);
  const editVersion = ref(0);
  const historyVersion = ref(0);
  let history: EditorHistory | null = null;
  let saveTimer: ReturnType<typeof setTimeout> | null = null;
  let saveInFlight = false;
  let loadController: AbortController | null = null;

  const canUndo = computed(() => {
    historyVersion.value;
    return history?.canUndo ?? false;
  });
  const canRedo = computed(() => {
    historyVersion.value;
    return history?.canRedo ?? false;
  });

  function clearSaveTimer(): void {
    if (saveTimer !== null) {
      clearTimeout(saveTimer);
      saveTimer = null;
    }
  }

  function scheduleSave(): void {
    clearSaveTimer();
    if (saveState.value === "conflict") {
      return;
    }
    saveTimer = setTimeout(() => {
      saveTimer = null;
      void saveNow();
    }, 800);
  }

  function markChanged(next: DashboardDocument): void {
    const hasConflict = saveState.value === "conflict";
    document.value = next;
    editVersion.value += 1;
    saveState.value = hasConflict ? "conflict" : "dirty";
    savingError.value = null;
    if (!hasConflict) {
      scheduleSave();
    }
  }

  async function load(screenId: string): Promise<void> {
    loadController?.abort();
    clearSaveTimer();
    const controller = new AbortController();
    loadController = controller;
    loading.value = true;
    loadError.value = null;
    saveState.value = "idle";
    try {
      const loaded = await getScreen(screenId, controller.signal);
      if (controller.signal.aborted) {
        return;
      }
      screen.value = loaded;
      document.value = structuredClone(loaded.draft_document);
      selection.value = [];
      history = new EditorHistory(loaded.draft_document);
      historyVersion.value += 1;
      editVersion.value = 0;
      saveState.value = "saved";
    } catch (reason) {
      if (!controller.signal.aborted) {
        loadError.value =
          reason instanceof ApiError
            ? reason
            : new ApiError({
                code: "SCREEN_LOAD_FAILED",
                message: "暂时无法加载大屏。",
                requestId: "",
                status: 500,
              });
      }
    } finally {
      if (!controller.signal.aborted) {
        loading.value = false;
      }
    }
  }

  function dispatch(command: EditorCommand): void {
    if (history === null || document.value === null) {
      throw new Error("The screen editor is not loaded.");
    }
    markChanged(history.execute(command));
    historyVersion.value += 1;
  }

  function applyChartSuggestion(
    componentId: string,
    chartSpec: ChartSpec,
  ): void {
    const current = document.value?.components?.find(
      (component) => component.id === componentId,
    );
    if (!current) {
      throw new Error(`Unknown component ID: ${componentId}`);
    }
    dispatch({
      type: "replace_component",
      component_id: componentId,
      component: createSuggestedComponent(current, chartSpec),
    });
  }

  function applyAiEdit(commands: readonly AiEditCommand[]): void {
    if (commands.length === 0) {
      return;
    }
    dispatch({
      type: "batch",
      commands: commands as unknown as EditorCommand[],
    });
  }

  function undo(): void {
    if (history?.canUndo) {
      markChanged(history.undo());
      historyVersion.value += 1;
    }
  }

  function redo(): void {
    if (history?.canRedo) {
      markChanged(history.redo());
      historyVersion.value += 1;
    }
  }

  async function saveNow(): Promise<void> {
    clearSaveTimer();
    if (
      screen.value === null ||
      document.value === null ||
      saveState.value === "conflict" ||
      saveState.value === "idle" ||
      saveState.value === "saved"
    ) {
      return;
    }
    if (saveInFlight) {
      return;
    }
    saveInFlight = true;
    const versionAtStart = editVersion.value;
    const documentAtStart: DashboardDocument = structuredClone(
      toRaw(document.value) as DashboardDocument,
    );
    saveState.value = "saving";
    savingError.value = null;
    try {
      const saved = await updateScreen(screen.value.id, {
        draft_document: documentAtStart,
        expected_revision: screen.value.draft_revision,
      });
      screen.value = saved;
      if (editVersion.value === versionAtStart) {
        document.value = structuredClone(saved.draft_document);
        saveState.value = "saved";
      } else {
        saveState.value = "dirty";
        scheduleSave();
      }
    } catch (reason) {
      const error =
        reason instanceof ApiError
          ? reason
          : new ApiError({
              code: "SCREEN_SAVE_FAILED",
              message: "暂时无法保存大屏。",
              requestId: "",
              status: 500,
            });
      savingError.value = error;
      if (error.code === "SCREEN_REVISION_CONFLICT") {
        saveState.value = "conflict";
        clearSaveTimer();
      } else {
        saveState.value = "failed";
      }
    } finally {
      saveInFlight = false;
    }
  }

  onScopeDispose(() => {
    clearSaveTimer();
    loadController?.abort();
  });

  return {
    canRedo,
    canUndo,
    dispatch,
    document,
    applyChartSuggestion,
    applyAiEdit,
    load,
    loadError,
    loading,
    redo,
    saveNow,
    saveState,
    savingError,
    screen,
    selection,
    undo,
  };
});
