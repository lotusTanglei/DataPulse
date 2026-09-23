import { apiRequest } from "../../lib/api";
import type { UserRole } from "../../stores/auth";
import type { UserResponse, GrantRequest, AuditResponse, ResourceAccessResponse } from "@datapulse/schema";

export type StudioUser = UserResponse;
export type ResourceType = "datasource" | "dataset" | "file" | "asset" | "screen";
export type ResourceGrant = GrantRequest;
export type IdentityAudit = AuditResponse;

export const getResourceAccess = (kind: ResourceType, id: string) => apiRequest<ResourceAccessResponse>(
  `/api/admin/identity/access/${kind}/${encodeURIComponent(id)}`,
);

export const listUsers = () => apiRequest<StudioUser[]>("/api/admin/users");
export const createUser = (payload: { username: string; password: string; role: UserRole }) =>
  apiRequest<StudioUser>("/api/admin/users", { method: "POST", json: payload });
export const updateUser = (id: string, payload: { role?: UserRole; active?: boolean; password?: string }) =>
  apiRequest<StudioUser>(`/api/admin/users/${encodeURIComponent(id)}`, { method: "PATCH", json: payload });
export const listDirectory = () => apiRequest<Pick<StudioUser, "id" | "username">[]>("/api/admin/identity/directory");
export const listIdentityAudit = () => apiRequest<IdentityAudit[]>("/api/admin/identity/audit");
export const listGrants = (resourceType: ResourceType, resourceId: string) => apiRequest<ResourceGrant[]>(
  `/api/admin/permissions?${new URLSearchParams({ resource_type: resourceType, resource_id: resourceId })}`,
);
export const saveGrant = (grant: ResourceGrant) => apiRequest<ResourceGrant>("/api/admin/permissions", { method: "PUT", json: grant });
export const revokeGrant = (grant: ResourceGrant) => apiRequest<void>(
  `/api/admin/permissions/${grant.resource_type}/${encodeURIComponent(grant.resource_id)}/${encodeURIComponent(grant.user_id)}`,
  { method: "DELETE" },
);
