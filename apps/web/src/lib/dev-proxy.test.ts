import { describe, expect, it } from "vitest";

import viteConfig from "../../vite.config";

describe("development API proxy", () => {
  it("preserves the browser Host header required by same-origin protection", () => {
    const apiProxy = viteConfig.server?.proxy?.["/api"];

    expect(apiProxy).toMatchObject({
      target: "http://127.0.0.1:8000",
      changeOrigin: false,
    });
  });
});
