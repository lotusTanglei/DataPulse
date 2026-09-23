import { mkdir, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { parseArgs } from "node:util";
import { compileFromFile } from "json-schema-to-typescript";

const root = resolve(import.meta.dirname, "..");
const { values } = parseArgs({ options: { "schema-dir": { type: "string" }, "output-dir": { type: "string" } } });
const schemaDir = resolve(values["schema-dir"] ?? resolve(root, "packages/schema/schemas"));
const outputRoot = resolve(values["output-dir"] ?? resolve(root, "packages/schema/src"));
const outputDir = resolve(outputRoot, "generated");

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
  exports.push(`export type { ${schema.title} } from "./generated/${name}.js";`);
}

await writeFile(resolve(outputRoot, "index.ts"), `${exports.join("\n")}\n`);
