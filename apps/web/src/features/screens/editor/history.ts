import type { DashboardDocument } from "../../../contracts";

import { applyCommand, type EditorCommand } from "./commands";

export class EditorHistory {
  readonly #limit: number;
  #current: DashboardDocument;
  #past: DashboardDocument[] = [];
  #future: DashboardDocument[] = [];

  constructor(document: DashboardDocument, limit = 100) {
    this.#current = structuredClone(document);
    this.#limit = limit;
  }

  get current(): DashboardDocument {
    return structuredClone(this.#current);
  }

  get canUndo(): boolean {
    return this.#past.length > 0;
  }

  get canRedo(): boolean {
    return this.#future.length > 0;
  }

  execute(command: EditorCommand): DashboardDocument {
    const previous = this.#current;
    const next = applyCommand(previous, command);
    this.#past.push(structuredClone(previous));
    if (this.#past.length > this.#limit) {
      this.#past.shift();
    }
    this.#current = next;
    this.#future = [];
    return this.current;
  }

  undo(): DashboardDocument {
    const previous = this.#past.pop();
    if (previous !== undefined) {
      this.#future.push(structuredClone(this.#current));
      this.#current = previous;
    }
    return this.current;
  }

  redo(): DashboardDocument {
    const next = this.#future.pop();
    if (next !== undefined) {
      this.#past.push(structuredClone(this.#current));
      this.#current = next;
    }
    return this.current;
  }
}
