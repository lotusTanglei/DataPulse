import { defineConfig, devices } from "@playwright/test";

import {
  loadRuntimeConfig,
  repositoryRoot,
} from "./e2e/runtime-config.js";

const runtime = loadRuntimeConfig();
const backendUrl = `http://127.0.0.1:${runtime.backendPort}`;
const frontendUrl = `http://127.0.0.1:${runtime.frontendPort}`;
const backendEnvironment = {
  DATAPULSE_ENVIRONMENT: "test",
  DATAPULSE_DATA_DIR: runtime.dataDir,
  DATAPULSE_BOOTSTRAP_CODE_OVERRIDE: runtime.setupCode,
  DATAPULSE_SIGNING_KEY: runtime.signingKey,
  DATAPULSE_STATIC_DIR: runtime.staticDir,
};

export default defineConfig({
  testDir: "./e2e",
  testIgnore: "**/*.target.spec.ts",
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  expect: { timeout: 8_000 },
  snapshotPathTemplate: "{testDir}/snapshots/{platform}/{arg}{ext}",
  globalTeardown: "./e2e/global-teardown.ts",
  use: {
    baseURL: frontendUrl,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
    },
  ],
  webServer: [
    {
      command:
        "uv run --package datapulse-server alembic -c apps/server/alembic.ini upgrade head && uv run --package datapulse-server uvicorn datapulse.app:app --host 127.0.0.1 --port " +
        runtime.backendPort,
      cwd: repositoryRoot,
      env: backendEnvironment,
      url: `${backendUrl}/api/auth/status`,
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command:
        "pnpm --filter @datapulse/web dev --host 127.0.0.1 --port " +
        runtime.frontendPort,
      cwd: repositoryRoot,
      env: {
        VITE_API_PROXY_TARGET: backendUrl,
      },
      url: `${frontendUrl}/studio`,
      reuseExistingServer: false,
      timeout: 30_000,
    },
  ],
});
