export type DeletedAssetCount = number;
export type DetachedTaskCount = number;

export interface DigitalHumanCacheClearResponse {
  deleted_asset_count: DeletedAssetCount;
  detached_task_count: DetachedTaskCount;
}
