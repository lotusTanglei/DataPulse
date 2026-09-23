export type CompatibleApi = string;
export type Description = string;
export type Path = string;
export type Sha256 = string;
export type Size = number;
export type Files = PackageFile[];
export type Id = string;
export type InstalledAt = string;
export type Kind = "plugin" | "template";
export type License = string;
export type Manifest = PluginManifest | TemplateManifest;
export type CompatibleApi1 = string;
/**
 * @minItems 1
 */
export type Components = [PluginComponent, ...PluginComponent[]];
export type Category = string;
export type JsonValue =
  | JsonValue[]
  | {
      [k: string]: JsonValue;
    }
  | string
  | boolean
  | number
  | number
  | null;
export type Name = string;
export type Type = string;
export type Description1 = string;
export type Entry = string;
export type Id1 = string;
export type License1 = string;
export type Name1 = string;
export type SchemaVersion = 1;
export type Source = string;
export type Version = string;
export type Assets = string[];
export type CompatibleApi2 = string;
export type Datasets = string[];
export type Description2 = string;
export type Document = "document.json";
export type Id2 = string;
export type Kind1 = "template";
export type License2 = string;
export type Name2 = string;
export type SchemaVersion1 = 1;
export type Source1 = string;
export type Version1 = string;
export type Name3 = string;
export type Sha2561 = string;
export type Source2 = string;
export type Version2 = string;

export interface CatalogPackage {
  compatible_api: CompatibleApi;
  description: Description;
  files: Files;
  id: Id;
  installed_at: InstalledAt;
  kind: Kind;
  license: License;
  manifest: Manifest;
  name: Name3;
  sha256: Sha2561;
  source: Source2;
  version: Version2;
}
export interface PackageFile {
  path: Path;
  sha256: Sha256;
  size: Size;
}
export interface PluginManifest {
  compatible_api: CompatibleApi1;
  components: Components;
  description?: Description1;
  entry: Entry;
  id: Id1;
  license?: License1;
  name: Name1;
  schema_version?: SchemaVersion;
  source?: Source;
  version: Version;
}
export interface PluginComponent {
  category: Category;
  data_schema: DataSchema;
  default_props?: DefaultProps;
  name: Name;
  property_schema: PropertySchema;
  type: Type;
}
export interface DataSchema {
  [k: string]: JsonValue;
}
export interface DefaultProps {
  [k: string]: JsonValue;
}
export interface PropertySchema {
  [k: string]: JsonValue;
}
export interface TemplateManifest {
  assets?: Assets;
  compatible_api: CompatibleApi2;
  datasets?: Datasets;
  description?: Description2;
  document?: Document;
  id: Id2;
  kind?: Kind1;
  license?: License2;
  name: Name2;
  schema_version?: SchemaVersion1;
  source?: Source1;
  version: Version1;
}
