import { expect, test, vi } from "vitest";

import type { JsonValue, QueryResult } from "../query/types";
import { createDataRuntime } from "./dataRuntime";

function queryResult(requestId: string, value: JsonValue): QueryResult {
  return {
    request_id: requestId,
    columns: [{ name: "value", data_type: "text" }],
    rows: [[value]],
    row_count: 1,
    truncated: false,
    duration_ms: 3,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, reject, resolve };
}

test("shares equal bindings and parameters within one refresh cycle", async () => {
  const query = vi
    .fn()
    .mockResolvedValue(queryResult("shared-query", "east"));
  const runtime = createDataRuntime(query);
  const binding = {
    dataset_id: "sales",
    chart: { type: "line", x: "date", y: "amount" },
  };

  const [first, second] = await Promise.all([
    runtime.load("line-a", binding, { region: "east" }),
    runtime.load("line-b", binding, { region: "east" }),
  ]);

  expect(first).toEqual(second);
  expect(query).toHaveBeenCalledTimes(1);
  expect(runtime.state("line-a").result).toEqual(first);
  expect(runtime.state("line-b").result).toEqual(second);
});

test("a new generation ignores a slower response from old parameters", async () => {
  const oldRequest = deferred<QueryResult>();
  const newRequest = deferred<QueryResult>();
  const query = vi
    .fn()
    .mockReturnValueOnce(oldRequest.promise)
    .mockReturnValueOnce(newRequest.promise);
  const runtime = createDataRuntime(query);
  const binding = { dataset_id: "sales", chart: { type: "kpi" } };

  const oldLoad = runtime.load("kpi-a", binding, { region: "east" });
  runtime.beginGeneration();
  const newLoad = runtime.load("kpi-a", binding, { region: "west" });

  newRequest.resolve(queryResult("new-query", 42));
  await newLoad;
  oldRequest.resolve(queryResult("old-query", 12));
  await oldLoad;

  expect(runtime.state("kpi-a")).toMatchObject({
    status: "success",
    result: { request_id: "new-query" },
  });
});

test("one failed query key does not reject or overwrite unrelated components", async () => {
  const query = vi.fn((componentId: string) => {
    if (componentId === "broken") {
      return Promise.reject(new Error("database unavailable"));
    }
    return Promise.resolve(queryResult("healthy-query", "ok"));
  });
  const runtime = createDataRuntime(query);

  const outcomes = await Promise.allSettled([
    runtime.load("broken", { dataset_id: "missing" }, {}),
    runtime.load("healthy", { dataset_id: "sales" }, {}),
  ]);

  expect(outcomes[0]?.status).toBe("rejected");
  expect(outcomes[1]).toMatchObject({
    status: "fulfilled",
    value: { request_id: "healthy-query" },
  });
  expect(runtime.state("broken").status).toBe("error");
  expect(runtime.state("healthy")).toMatchObject({
    status: "success",
    result: { request_id: "healthy-query" },
  });
});
