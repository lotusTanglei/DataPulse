export type Assets = string[];
export type CompatibleApi = string;
export type Datasets = string[];
export type Description = string;
export type Document = "document.json";
export type Id = string;
export type Kind = "template";
export type License = string;
export type Name = string;
export type SchemaVersion = 1;
export type Source = string;
export type Version = string;

export interface TemplateManifest {
  assets?: Assets;
  compatible_api: CompatibleApi;
  datasets?: Datasets;
  description?: Description;
  document?: Document;
  id: Id;
  kind?: Kind;
  license?: License;
  name: Name;
  schema_version?: SchemaVersion;
  source?: Source;
  version: Version;
}
