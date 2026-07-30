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
};

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  expect: { timeout: 8_000 },
  snapshotPathTemplate: "{testDir}/snapshots/{arg}{ext}",
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
