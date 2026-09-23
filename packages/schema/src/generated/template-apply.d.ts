export type Description = string;
export type Name = string;

export interface TemplateApply {
  asset_mapping?: AssetMapping;
  dataset_mapping?: DatasetMapping;
  description?: Description;
  name: Name;
}
export interface AssetMapping {
  [k: string]: string;
}
export interface DatasetMapping {
  [k: string]: string;
}
