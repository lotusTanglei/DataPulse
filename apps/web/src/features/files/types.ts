export type FileFormat = "csv" | "excel" | "json" | "parquet";

export interface FileAssetField {
  name: string;
  data_type: string;
}

export interface FileAsset {
  id: string;
  original_name: string;
  format: FileFormat;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  row_count: number;
  fields: FileAssetField[];
  created_at: string;
}
