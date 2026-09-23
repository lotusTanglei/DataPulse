export type Source = "components";
/**
 * @minItems 1
 * @maxItems 50
 */
export type Variables = [DigitalHumanVariable, ...DigitalHumanVariable[]];
export type ComponentId = string;
export type Field = string;
export type Name = string;
export type Row = number;
export type Unit = string;

export interface DigitalHumanBinding {
  source?: Source;
  variables: Variables;
}
export interface DigitalHumanVariable {
  component_id: ComponentId;
  enum_labels?: EnumLabels;
  field: Field;
  name: Name;
  row?: Row;
  unit?: Unit;
}
export interface EnumLabels {
  [k: string]: string;
}
