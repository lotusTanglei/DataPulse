import { fileURLToPath } from "node:url";
import { defineConfig } from "../../apps/web/node_modules/vite";
export default defineConfig({
  build: {
    outDir: fileURLToPath(new URL("./dist", import.meta.url)),
    emptyOutDir: true,
    lib: {
      entry: fileURLToPath(new URL("./src/index.ts", import.meta.url)),
      formats: ["es"],
      fileName: () => "index.mjs",
    },
    rollupOptions: { output: { inlineDynamicImports: true } },
    minify: false,
  },
});
