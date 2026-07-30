export interface FieldError {
  field: string;
  message: string;
}

interface ErrorEnvelope {
  error: {
    code: string;
    message: string;
    request_id: string;
    field_errors: FieldError[];
  };
}

export interface HealthResponse {
  status: string;
  version: string;
}

export interface ApiRequestInit extends Omit<RequestInit, "body"> {
  body?: BodyInit | null;
  json?: unknown;
}

export const AUTH_EXPIRED_EVENT = "datapulse:auth-expired";

export class ApiError extends Error {
  readonly code: string;
  readonly requestId: string;
  readonly fieldErrors: FieldError[];
  readonly status: number;

  constructor(options: {
    code: string;
    message: string;
    requestId: string;
    fieldErrors?: FieldError[];
    status: number;
  }) {
    super(options.message);
    this.name = "ApiError";
    this.code = options.code;
    this.requestId = options.requestId;
    this.fieldErrors = options.fieldErrors ?? [];
    this.status = options.status;
  }
}

function cookie(name: string): string | null {
  for (const part of document.cookie.split(";")) {
    const [key, ...value] = part.trim().split("=");
    if (key === name) {
      try {
        return decodeURIComponent(value.join("="));
      } catch {
        return value.join("=");
      }
    }
  }
  return null;
}

function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  if (typeof value !== "object" || value === null || !("error" in value)) {
    return false;
  }
  const error = value.error;
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    typeof error.code === "string" &&
    "message" in error &&
    typeof error.message === "string" &&
    "request_id" in error &&
    typeof error.request_id === "string" &&
    "field_errors" in error &&
    Array.isArray(error.field_errors)
  );
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (isErrorEnvelope(payload)) {
    return new ApiError({
      code: payload.error.code,
      message: payload.error.message,
      requestId: payload.error.request_id,
      fieldErrors: payload.error.field_errors,
      status: response.status,
    });
  }
  return new ApiError({
    code: "HTTP_ERROR",
    message: "请求失败，请稍后重试。",
    requestId: response.headers?.get("X-Request-ID") ?? "",
    status: response.status,
  });
}

export async function apiRequest<T>(
  input: RequestInfo | URL,
  options: ApiRequestInit = {},
): Promise<T> {
  const { json, ...requestOptions } = options;
  const method = (requestOptions.method ?? "GET").toUpperCase();
  const headers = new Headers(requestOptions.headers);
  if (["POST", "PATCH", "DELETE"].includes(method)) {
    const csrfToken = cookie("datapulse_csrf");
    if (csrfToken !== null) {
      headers.set("X-CSRF-Token", csrfToken);
    }
  }
  let body = requestOptions.body;
  if (json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(json);
  }
  const response = await fetch(input, {
    ...requestOptions,
    method,
    headers,
    body,
    credentials: "same-origin",
  });
  if (!response.ok) {
    const error = await errorFromResponse(response);
    if (response.status === 401) {
      window.dispatchEvent(
        new CustomEvent<ApiError>(AUTH_EXPIRED_EVENT, { detail: error }),
      );
    }
    throw error;
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export function getHealth(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>("/api/health");
}
