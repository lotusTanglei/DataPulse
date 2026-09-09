import { defineConfig } from "@playwright/test";

import baseConfig from "./playwright.config.js";

export default defineConfig({
  ...baseConfig,
  testIgnore: undefined,
  testMatch: "**/*.target.spec.ts",
  projects: [
    {
      name: "chromium",
      use: {
        browserName: "chromium",
        channel: "chrome",
        viewport: null,
      },
    },
  ],
});
