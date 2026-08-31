import { shallowReactive } from "vue";

import type { JsonValue, QueryResult } from "../query/types";
import type {
  ComponentQueryState,
  DataBinding,
  QueryComponent,
  RuntimeParameters,
} from "./types";
import { resolveLocalResult } from "./mockData";

const IDLE_STATE: ComponentQueryState = {
  status: "idle",
  result: null,
  error: null,
};

function canonicalize(value: JsonValue): JsonValue {
  if (Array.isArray(value)) {
    return value.map(canonicalize);
  }
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value)
        .sort(([first], [second]) => first.localeCompare(second))
        .map(([key, item]) => [key, canonicalize(item)]),
    );
  }
  return value;
}

function queryKey(
  binding: DataBinding,
  parameters: RuntimeParameters,
): string {
  return JSON.stringify(canonicalize({ binding, parameters }));
}

export interface DataRuntime {
  beginGeneration(): number;
  dispose(): void;
  load(
    componentId: string,
    binding: DataBinding,
    parameters: RuntimeParameters,
    componentType?: string,
  ): Promise<QueryResult>;
  state(componentId: string): ComponentQueryState;
}

export function createDataRuntime(queryComponent: QueryComponent): DataRuntime {
  const states = shallowReactive(new Map<string, ComponentQueryState>());
  const cycleRequests = new Map<string, Promise<QueryResult>>();
  const controllers = new Map<string, AbortController>();
  const componentLoads = new Map<string, number>();
  let generation = 0;
  let loadSequence = 0;
  let disposed = false;

  function beginGeneration(): number {
    generation += 1;
    for (const controller of controllers.values()) {
      controller.abort();
    }
    controllers.clear();
    cycleRequests.clear();
    return generation;
  }

  async function load(
    componentId: string,
    binding: DataBinding,
    parameters: RuntimeParameters,
    componentType?: string,
  ): Promise<QueryResult> {
    if (disposed) {
      throw new Error("The data runtime has been disposed.");
    }
    const requestGeneration = generation;
    const componentLoad = ++loadSequence;
    componentLoads.set(componentId, componentLoad);
    states.set(componentId, {
      status: "loading",
      result: states.get(componentId)?.result ?? null,
      error: null,
    });

    let localResult: QueryResult | null = null;
    try {
      localResult = resolveLocalResult(
        { id: componentId, type: componentType ?? "builtin.table" },
        binding,
      );
    } catch (error) {
      states.set(componentId, { status: "error", result: null, error });
      throw error;
    }

    const key = queryKey(binding, parameters);
    let request = cycleRequests.get(key);
    if (localResult) {
      request = Promise.resolve(localResult);
    } else if (!request) {
      const controller = new AbortController();
      controllers.set(key, controller);
      request = Promise.resolve().then(() =>
        queryComponent(
          componentId,
          structuredClone(parameters),
          controller.signal,
        ),
      );
      cycleRequests.set(key, request);
      const releaseController = () => {
        if (controllers.get(key) === controller) {
          controllers.delete(key);
        }
      };
      void request.then(releaseController, releaseController);
    }

    try {
      const result = await request;
      if (
        !disposed &&
        generation === requestGeneration &&
        componentLoads.get(componentId) === componentLoad
      ) {
        states.set(componentId, {
          status: "success",
          result,
          error: null,
        });
      }
      return result;
    } catch (error) {
      if (
        !disposed &&
        generation === requestGeneration &&
        componentLoads.get(componentId) === componentLoad
      ) {
        states.set(componentId, {
          status: "error",
          result: null,
          error,
        });
      }
      throw error;
    }
  }

  return {
    beginGeneration,
    dispose() {
      disposed = true;
      beginGeneration();
      states.clear();
      componentLoads.clear();
    },
    load,
    state(componentId) {
      return states.get(componentId) ?? IDLE_STATE;
    },
  };
}
