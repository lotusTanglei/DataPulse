export type Permission = "read" | "write" | "publish";
export type Identifier = string;
export type ResourceType = "datasource" | "dataset" | "file" | "asset" | "screen";

export interface GrantRequest {
  permission: Permission;
  resource_id: Identifier;
  resource_type: ResourceType;
  user_id: Identifier;
}
