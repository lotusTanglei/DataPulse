export type CompatibleApi = string;
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
export type Entry = string;
export type Id = string;
export type Name1 = string;
export type SchemaVersion = 1;
export type Version = string;

export interface PluginManifest {
  compatible_api: CompatibleApi;
  components: Components;
  entry: Entry;
  id: Id;
  name: Name1;
  schema_version?: SchemaVersion;
  version: Version;
}
export interface PluginComponent {
  category: Category;
  data_schema: DataSchema;
  name: Name;
  property_schema: PropertySchema;
  type: Type;
}
export interface DataSchema {
  [k: string]: JsonValue;
}
export interface PropertySchema {
  [k: string]: JsonValue;
}
