import { expect, test, vi } from "vitest";
import { createSpeechQueue, type SpeechQueueTask } from "./speechQueue";

function deferredTask(id: string, owner = "speaker"): SpeechQueueTask {
  return {
    id, owner, priority: 0, expiresAt: 1000, cancel: vi.fn(),
    run: vi.fn((signal: AbortSignal) => new Promise<void>((resolve) => signal.addEventListener("abort", () => resolve(), { once: true }))),
  };
}
async function flush(): Promise<void> {
  for (let index = 0; index < 10; index++) await Promise.resolve();
}

test("serializes sounds across components and waits for the canceled driver", async () => {
  const queue = createSpeechQueue(() => 0);
  const first = deferredTask("first");
  const second = deferredTask("second", "other");
  queue.enqueue(first, "queue", 2);
  queue.enqueue(second, "queue", 2);
  await flush();
  expect(first.run).toHaveBeenCalledOnce();
  expect(second.run).not.toHaveBeenCalled();
  queue.cancel("speaker");
  await flush();
  expect(second.run).toHaveBeenCalledOnce();
  queue.cancel("other");
  await flush();
  expect(queue.size()).toBe(0);
});

test("merges only pending tasks for the same owner and bounds the queue", async () => {
  const queue = createSpeechQueue(() => 0);
  const active = deferredTask("active");
  const discarded = deferredTask("old");
  const latest = deferredTask("latest");
  queue.enqueue(active, "queue", 1);
  await flush();
  expect(queue.enqueue(discarded, "queue", 1)).toBe(true);
  expect(queue.enqueue(deferredTask("overflow"), "queue", 1)).toBe(false);
  expect(queue.enqueue(latest, "merge", 1)).toBe(true);
  expect(discarded.cancel).toHaveBeenCalledOnce();
  expect(active.cancel).not.toHaveBeenCalled();
  queue.cancel("speaker");
  await flush();
  expect(latest.run).not.toHaveBeenCalled();
  expect(queue.size()).toBe(0);
});

test("expires queued speech without playing stale content", async () => {
  let now = 0;
  const queue = createSpeechQueue(() => now);
  const active = deferredTask("active");
  const stale = deferredTask("stale", "other");
  queue.enqueue(active, "queue", 1);
  queue.enqueue(stale, "queue", 1);
  await flush();
  now = 2000;
  queue.cancel("speaker");
  await flush();
  expect(stale.run).not.toHaveBeenCalled();
  expect(stale.cancel).toHaveBeenCalledOnce();
  expect(queue.size()).toBe(0);
});

test("drop_old keeps pending work until the owner reaches its limit, then removes only the oldest", async () => {
  const queue = createSpeechQueue(() => 0);
  const active = deferredTask("active", "active");
  const first = deferredTask("first");
  const second = deferredTask("second");
  const latest = deferredTask("latest");
  queue.enqueue(active, "queue", 3);
  await flush();
  queue.enqueue(first, "drop_old", 2);
  queue.enqueue(second, "drop_old", 2);
  expect(queue.enqueue(latest, "drop_old", 2)).toBe(true);
  expect(first.cancel).toHaveBeenCalledOnce();
  expect(second.cancel).not.toHaveBeenCalled();
  second.run = vi.fn(async () => undefined);
  latest.run = vi.fn(async () => undefined);
  queue.cancel("active");
  await flush();
  expect(second.run).toHaveBeenCalledOnce();
  await flush();
  expect(latest.run).toHaveBeenCalledOnce();
});

test("interrupt releases the global audio focus even when another owner is speaking", async () => {
  const queue = createSpeechQueue(() => 0);
  const first = deferredTask("first", "one");
  const replacement = deferredTask("replacement", "two");
  queue.enqueue(first, "queue", 2);
  await flush();
  expect(queue.enqueue(replacement, "interrupt", 2)).toBe(true);
  expect(first.cancel).toHaveBeenCalledOnce();
  await flush();
  expect(replacement.run).toHaveBeenCalledOnce();
  queue.cancel("two");
  await flush();
});

test("priority is descending and equal priorities remain FIFO", async () => {
  const queue = createSpeechQueue(() => 0);
  const active = deferredTask("active", "active");
  const low = deferredTask("low", "low");
  const high = deferredTask("high", "high");
  const equal = deferredTask("equal", "equal");
  low.priority = 1;
  high.priority = 10;
  equal.priority = 10;
  queue.enqueue(active, "queue", 1);
  await flush();
  queue.enqueue(low, "queue", 1);
  queue.enqueue(high, "queue", 1);
  queue.enqueue(equal, "queue", 1);
  queue.cancel("active");
  await flush();
  expect(high.run).toHaveBeenCalledOnce();
  queue.cancel("high");
  await flush();
  expect(equal.run).toHaveBeenCalledOnce();
});
