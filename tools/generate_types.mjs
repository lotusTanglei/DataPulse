import { mkdir, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { compileFromFile } from "json-schema-to-typescript";

const root = resolve(import.meta.dirname, "..");
const schemaDir = resolve(root, "packages/schema/schemas");
const outputDir = resolve(root, "packages/schema/src/generated");

await mkdir(outputDir, { recursive: true });
for (const oldFile of await readdir(outputDir).catch(() => [])) {
  if (oldFile.endsWith(".d.ts")) {
    await rm(resolve(outputDir, oldFile));
  }
}

const schemaFiles = (await readdir(schemaDir))
  .filter((file) => file.endsWith(".schema.json"))
  .sort();
const exports = [];

for (const file of schemaFiles) {
  const name = file.replace(".schema.json", "");
  const schemaPath = resolve(schemaDir, file);
  const schema = JSON.parse(await readFile(schemaPath, "utf8"));
  const output = await compileFromFile(schemaPath, {
    bannerComment: "",
  });
  await writeFile(resolve(outputDir, `${name}.d.ts`), output);
  exports.push(`export type { ${schema.title} } from "./generated/${name}";`);
}

await writeFile(resolve(root, "packages/schema/src/index.ts"), `${exports.join("\n")}\n`);
