import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";

import type { Datasource } from "../datasources/types";
import SqlDebugView from "./SqlDebugView.vue";
import SqlEditor from "./SqlEditor.vue";

const adapterCalls: Array<{
  dialect: string;
  setDialect: ReturnType<typeof vi.fn>;
  setValue: ReturnType<typeof vi.fn>;
  destroy: ReturnType<typeof vi.fn>;
}> = [];

vi.mock("./editorAdapter", () => ({
  createSqlEditor(options: {
    parent: HTMLElement;
    initialValue: string;
    dialect: string;
    onChange: (value: string) => void;
    onRun: () => void;
  }) {
    const textarea = document.createElement("textarea");
    textarea.className = "sql-editor-input";
    textarea.value = options.initialValue;
    textarea.addEventListener("input", () => options.onChange(textarea.value));
    textarea.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        options.onRun();
      }
    });
    options.parent.append(textarea);
    const adapter = {
      dialect: options.dialect,
      setDialect: vi.fn(),
      setValue: vi.fn((value: string) => {
        textarea.value = value;
      }),
      destroy: vi.fn(() => textarea.remove()),
      focus: vi.fn(),
    };
    adapterCalls.push(adapter);
    return adapter;
  },
}));

const datasource: Datasource = {
  id: "source-1",
  name: "分析仓库",
  config: {
    type: "postgresql",
    host: "db.internal",
    port: 5432,
    database: "analytics",
    username: "reporter",
    ssl_mode: "require",
  },
  status: "available",
  has_password: true,
  last_checked_at: "2026-07-30T03:00:00Z",
  last_latency_ms: 18,
  last_error_code: null,
  created_at: "2026-07-28T08:00:00Z",
  updated_at: "2026-07-30T03:00:00Z",
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  adapterCalls.splice(0);
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("uses the source dialect and emits one run for either keyboard shortcut", async () => {
  const wrapper = mount(SqlEditor, {
    props: {
      modelValue: "SELECT 1",
      dialect: "postgresql",
    },
  });

  expect(adapterCalls[0]?.dialect).toBe("postgresql");
  const input = wrapper.get("textarea");
  await input.trigger("keydown", { key: "Enter", metaKey: true });
  await input.trigger("keydown", { key: "Enter", ctrlKey: true });
  expect(wrapper.emitted("run")).toHaveLength(2);

  await wrapper.setProps({ dialect: "mysql" });
  expect(adapterCalls[0]?.setDialect).toHaveBeenCalledWith("mysql");
});

test("shows safety limits, preserves SQL on errors, and cancels superseded work", async () => {
  let firstSignal: AbortSignal | undefined;
  const fetchMock = vi.fn(
    (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      expect(String(input)).toBe("/api/admin/datasources/source-1/query");
      if (firstSignal === undefined) {
        firstSignal = init?.signal ?? undefined;
        return new Promise<Response>(() => undefined);
      }
      return Promise.resolve(
        jsonResponse(
          {
            error: {
              code: "QUERY_EXECUTION_FAILED",
              message: "查询执行失败。",
              request_id: "query-error-17",
              field_errors: [],
            },
          },
          422,
        ),
      );
    },
  );
  vi.stubGlobal("fetch", fetchMock);

  const wrapper = mount(SqlDebugView, {
    props: { datasource },
    global: {
      stubs: {
        SchemaBrowser: { template: "<aside>Schema browser</aside>" },
        SaveDatasetDialog: true,
      },
    },
  });

  expect(wrapper.text()).toContain("只读查询");
  expect(wrapper.text()).toContain("30 秒");
  expect(wrapper.text()).toContain("5,000 行");

  const input = wrapper.get("textarea");
  await input.setValue("SELECT amount FROM sales");
  await wrapper.get('[data-action="run-query"]').trigger("click");
  expect(wrapper.text()).toContain("正在运行");
  await wrapper.get('[data-action="run-query"]').trigger("click");
  await flushPromises();

  expect(firstSignal?.aborted).toBe(true);
  expect((wrapper.get("textarea").element as HTMLTextAreaElement).value).toBe(
    "SELECT amount FROM sales",
  );
  expect(wrapper.text()).toContain("查询执行失败。");
  expect(wrapper.text()).toContain("QUERY_EXECUTION_FAILED");
  expect(wrapper.text()).toContain("query-error-17");
});

test("aborts the active query when the workspace unmounts", async () => {
  let activeSignal: AbortSignal | undefined;
  vi.stubGlobal(
    "fetch",
    vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      activeSignal = init?.signal ?? undefined;
      return new Promise<Response>(() => undefined);
    }),
  );
  const wrapper = mount(SqlDebugView, {
    props: { datasource },
    global: {
      stubs: {
        SchemaBrowser: { template: "<aside>Schema browser</aside>" },
        SaveDatasetDialog: true,
      },
    },
  });

  await wrapper.get('[data-action="run-query"]').trigger("click");
  wrapper.unmount();
  expect(activeSignal?.aborted).toBe(true);
});
