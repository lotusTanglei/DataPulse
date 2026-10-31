export type Category = string;
export type JsonValue =
  | JsonValue[]
  | {
      [k: string]: JsonValue;
    }
  | string
  | boolean
  | number
  | null;
export type SchemaVersion = 1;
export type Type = string;
export type Version = string;

export interface ComponentContract {
  category: Category;
  data_input_schema: DataInputSchema;
  default_props?: DefaultProps;
  props_schema: PropsSchema;
  schema_version?: SchemaVersion;
  type: Type;
  version: Version;
}
export interface DataInputSchema {
  [k: string]: JsonValue;
}
export interface DefaultProps {
  [k: string]: JsonValue;
}
export interface PropsSchema {
  [k: string]: JsonValue;
}
