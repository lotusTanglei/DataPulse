export interface SpeechQueueTask {
  id: string;
  owner: string;
  expiresAt: number;
  priority: number;
  run(signal: AbortSignal): Promise<void>;
  cancel(): void;
}

export type SpeechQueuePolicy = "queue" | "merge" | "drop_old" | "interrupt";

export function createSpeechQueue(now: () => number = Date.now) {
  const pending: Array<{ task: SpeechQueueTask; sequence: number }> = [];
  let active: { task: SpeechQueueTask; controller: AbortController } | null = null;
  let sequence = 0;

  function advance(): void {
    if (active) return;
    while (pending.length) {
      const pendingEntry = pending.shift()!;
      const task = pendingEntry.task;
      if (task.expiresAt <= now()) {
        task.cancel();
        continue;
      }
      const controller = new AbortController();
      const entry = { task, controller };
      active = entry;
      void Promise.resolve().then(() => {
        if (!controller.signal.aborted) return task.run(controller.signal);
      }).catch(() => {
        task.cancel();
      }).finally(() => {
        if (active === entry) active = null;
        advance();
      });
      return;
    }
  }

  function cancel(owner: string, includeActive = true): void {
    for (let index = pending.length - 1; index >= 0; index--) {
      if (pending[index]!.task.owner === owner) pending.splice(index, 1)[0]!.task.cancel();
    }
    if (includeActive && active?.task.owner === owner) {
      // Keep focus until the canceled driver releases its media resources.
      active.controller.abort();
      active.task.cancel();
    }
  }

  function cancelActive(): void {
    if (!active) return;
    active.controller.abort();
    active.task.cancel();
  }

  return {
    enqueue(task: SpeechQueueTask, policy: SpeechQueuePolicy, maxLength: number): boolean {
      if (task.expiresAt <= now()) return false;
      if (policy === "interrupt") {
        cancelActive();
        cancel(task.owner, false);
      }
      const owned = pending.filter((item) => item.task.owner === task.owner);
      if (policy === "merge") {
        for (let index = pending.length - 1; index >= 0; index--) {
          if (pending[index]!.task.owner === task.owner) pending.splice(index, 1)[0]!.task.cancel();
        }
      } else if (policy === "drop_old" && owned.length >= maxLength) {
        const oldest = pending.findIndex((item) => item.task.owner === task.owner);
        if (oldest >= 0) pending.splice(oldest, 1)[0]!.task.cancel();
      } else if (policy === "queue" && owned.length >= maxLength) {
        return false;
      }
      pending.push({ task, sequence: sequence++ });
      pending.sort((first, second) => second.task.priority - first.task.priority || first.sequence - second.sequence);
      advance();
      return true;
    },
    cancel,
    size: () => pending.length + (active ? 1 : 0),
  };
}

// One sound at a time across all screen instances in the same browsing context.
export const pageSpeechQueue = createSpeechQueue();
