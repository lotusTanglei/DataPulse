import { markRaw } from "vue";

import type { ComponentDefinition } from "./types";

export class ComponentRegistry {
  readonly #definitions = new Map<string, ComponentDefinition>();

  constructor() {
    markRaw(this);
  }

  register(definition: ComponentDefinition): this {
    if (this.#definitions.has(definition.type)) {
      throw new Error(
        `Component type is already registered: ${definition.type}`,
      );
    }
    this.#definitions.set(definition.type, definition);
    return this;
  }

  get(type: string): ComponentDefinition | undefined {
    return this.#definitions.get(type);
  }

  has(type: string): boolean {
    return this.#definitions.has(type);
  }

  list(): ComponentDefinition[] {
    return [...this.#definitions.values()];
  }
}

export const defaultComponentRegistry = new ComponentRegistry();
