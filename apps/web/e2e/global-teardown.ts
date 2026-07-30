import { readFile, realpath, rm, unlink } from "node:fs/promises";
import { tmpdir } from "node:os";
import { basename, dirname } from "node:path";

import type { E2EConfig } from "./runtime-config.js";
import { runtimeConfigPath } from "./runtime-config.js";

export default async function globalTeardown(): Promise<void> {
  const configPath = runtimeConfigPath();
  let config: E2EConfig;
  try {
    config = JSON.parse(await readFile(configPath, "utf8")) as E2EConfig;
  } catch {
    return;
  }

  const dataDir = await realpath(config.dataDir);
  const systemTempDir = await realpath(tmpdir());
  if (
    dirname(dataDir) !== systemTempDir ||
    !basename(dataDir).startsWith("datapulse-e2e-")
  ) {
    throw new Error(`Refusing to remove unsafe E2E directory: ${dataDir}`);
  }
  await rm(dataDir, { recursive: true });
  await unlink(configPath);
}
