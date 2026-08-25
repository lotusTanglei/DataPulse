import { readFileSync } from "node:fs";
import { basename, dirname, resolve } from "node:path";

export interface E2EConfig {
  backendPort: number;
  frontendPort: number;
  dataDir: string;
  staticDir: string;
  setupCode: string;
  signingKey: string;
}

export const repositoryRoot = resolve(import.meta.dirname, "../../..");

export function runtimeConfigPath(): string {
  const value = process.env.DATAPULSE_E2E_CONFIG;
  if (value === undefined) {
    throw new Error(
      "DATAPULSE_E2E_CONFIG is missing; run E2E through `pnpm test:e2e`.",
    );
  }
  const runtimeRoot = resolve(repositoryRoot, ".e2e");
  const configPath = resolve(value);
  if (
    dirname(configPath) !== runtimeRoot ||
    !basename(configPath).startsWith("config-") ||
    !basename(configPath).endsWith(".json")
  ) {
    throw new Error(`Refusing to use unsafe E2E config: ${configPath}`);
  }
  return configPath;
}

export function loadRuntimeConfig(): E2EConfig {
  return JSON.parse(
    readFileSync(runtimeConfigPath(), "utf8"),
  ) as E2EConfig;
}
