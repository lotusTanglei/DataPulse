import { defineStore } from "pinia";
import { ref } from "vue";

import { ApiError, apiRequest } from "../lib/api";

export type UserRole = "admin" | "editor" | "viewer";

export type AuthState =
  | { status: "unknown" }
  | { status: "setup-required" }
  | { status: "anonymous" }
  | { status: "authenticated"; username: string; id?: string; role?: UserRole };

export interface SetupPayload {
  code: string;
  username: string;
  password: string;
}

export interface LoginPayload {
  username: string;
  password: string;
}

interface AuthStatusResponse {
  initialized: boolean;
}

interface SessionResponse {
  username: string;
  id?: string;
  role?: UserRole;
}

export const useAuthStore = defineStore("auth", () => {
  const state = ref<AuthState>({ status: "unknown" });
  let resolving: Promise<AuthState> | null = null;

  async function resolve(): Promise<AuthState> {
    if (state.value.status !== "unknown") {
      return state.value;
    }
    if (resolving !== null) {
      return resolving;
    }
    resolving = (async () => {
      let status: AuthStatusResponse;
      try {
        status = await apiRequest<AuthStatusResponse>("/api/auth/status");
      } catch (error) {
        if (error instanceof ApiError && error.status >= 500) {
          state.value = { status: "anonymous" };
          return state.value;
        }
        throw error;
      }
      if (!status.initialized) {
        state.value = { status: "setup-required" };
        return state.value;
      }
      try {
        const session = await apiRequest<SessionResponse>("/api/auth/session");
        state.value = {
          status: "authenticated",
          ...session,
        };
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          state.value = { status: "anonymous" };
        } else {
          throw error;
        }
      }
      return state.value;
    })();
    try {
      return await resolving;
    } finally {
      resolving = null;
    }
  }

  async function setup(payload: SetupPayload): Promise<void> {
    const session = await apiRequest<SessionResponse>("/api/auth/setup", {
      method: "POST",
      json: payload,
    });
    state.value = {
      status: "authenticated",
      ...session,
    };
  }

  async function login(payload: LoginPayload): Promise<void> {
    await apiRequest<void>("/api/auth/login", {
      method: "POST",
      json: payload,
    });
    const session = await apiRequest<SessionResponse>("/api/auth/session");
    state.value = {
      status: "authenticated",
      ...session,
    };
  }

  async function logout(): Promise<void> {
    await apiRequest<void>("/api/auth/logout", { method: "POST" });
    state.value = { status: "anonymous" };
  }

  function expire(): void {
    state.value = { status: "anonymous" };
  }

  return {
    state,
    resolve,
    setup,
    login,
    logout,
    expire,
  };
});
