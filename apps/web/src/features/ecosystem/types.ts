import type { JsonValue } from "../query/types";

export interface PluginComponentManifest {
  type: string;
  name: string;
  category: string;
  property_schema: Record<string, JsonValue>;
  data_schema: Record<string, JsonValue>;
  default_props?: Record<string, JsonValue>;
}
export interface PluginManifest {
  schema_version?: 1;
  id: string;
  version: string;
  compatible_api: string;
  name: string;
  description?: string;
  license?: string;
  source?: string;
  entry: string;
  components: PluginComponentManifest[];
}
export interface TemplateManifest {
  kind: "template";
  schema_version?: 1;
  id: string;
  version: string;
  compatible_api: string;
  name: string;
  description?: string;
  license?: string;
  source?: string;
  document: "document.json";
  datasets: string[];
  assets: string[];
}
interface PackageMetadata {
  id: string;
  version: string;
  name: string;
  description: string;
  license: string;
  source: string;
  compatible_api: string;
  sha256: string;
  installed_at: string;
  files: Array<{ path: string; sha256: string; size: number }>;
}
export type CatalogPackage = PackageMetadata &
  (
    | { kind: "plugin"; manifest: PluginManifest }
    | { kind: "template"; manifest: TemplateManifest }
  );
export type PluginPackage = Extract<CatalogPackage, { kind: "plugin" }>;
export interface TemplateApply {
  name: string;
  description?: string;
  dataset_mapping: Record<string, string>;
  asset_mapping: Record<string, string>;
}
