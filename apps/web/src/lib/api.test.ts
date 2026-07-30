import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import {
  AUTH_EXPIRED_EVENT,
  ApiError,
  apiRequest,
} from "./api";

function response(body: object | null, status = 200): Response {
  return new Response(body === null ? null : JSON.stringify(body), {
    status,
    headers: body === null ? undefined : { "Content-Type": "application/json" },
  });
}

function requestInit(fetchMock: ReturnType<typeof vi.fn>): RequestInit {
  return fetchMock.mock.calls[0]?.[1] as RequestInit;
}

beforeEach(() => {
  document.cookie = "datapulse_csrf=; Max-Age=0; Path=/";
  document.cookie = "not_datapulse_csrf=; Max-Age=0; Path=/";
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("apiRequest", () => {
  test("uses same-origin credentials and leaves GET requests without CSRF", async () => {
    document.cookie = "datapulse_csrf=csrf-token; Path=/";
    const fetchMock = vi.fn().mockResolvedValue(response({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await apiRequest<{ ok: boolean }>("/api/example");

    expect(requestInit(fetchMock).credentials).toBe("same-origin");
    expect(new Headers(requestInit(fetchMock).headers).has("X-CSRF-Token")).toBe(false);
  });

  test.each(["POST", "PATCH", "DELETE"])(
    "adds only the exact CSRF cookie to %s requests",
    async (method) => {
      document.cookie = "not_datapulse_csrf=wrong-token; Path=/";
      document.cookie = "datapulse_csrf=right%20token; Path=/";
      const fetchMock = vi.fn().mockResolvedValue(response({ ok: true }));
      vi.stubGlobal("fetch", fetchMock);

      await apiRequest("/api/example", { method });

      expect(new Headers(requestInit(fetchMock).headers).get("X-CSRF-Token")).toBe(
        "right token",
      );
    },
  );

  test("throws a structured ApiError without losing request metadata", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        response(
          {
            error: {
              code: "REQUEST_VALIDATION_ERROR",
              message: "The request is invalid.",
              request_id: "request-123",
              field_errors: [
                { field: "username", message: "Username is required." },
              ],
            },
          },
          422,
        ),
      ),
    );

    const error = await apiRequest("/api/example").catch((reason: unknown) => reason);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      code: "REQUEST_VALIDATION_ERROR",
      message: "The request is invalid.",
      requestId: "request-123",
      fieldErrors: [{ field: "username", message: "Username is required." }],
      status: 422,
    });
  });

  test("dispatches the original ApiError when authentication expires", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        response(
          {
            error: {
              code: "AUTH_REQUIRED",
              message: "Authentication is required.",
              request_id: "expired-1",
              field_errors: [],
            },
          },
          401,
        ),
      ),
    );
    const listener = vi.fn();
    window.addEventListener(AUTH_EXPIRED_EVENT, listener);

    const error = await apiRequest("/api/admin/datasources").catch(
      (reason: unknown) => reason,
    );

    expect(error).toBeInstanceOf(ApiError);
    expect(listener).toHaveBeenCalledOnce();
    expect((listener.mock.calls[0]?.[0] as CustomEvent).detail).toBe(error);

    window.removeEventListener(AUTH_EXPIRED_EVENT, listener);
  });
});
