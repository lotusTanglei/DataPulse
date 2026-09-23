export type Action = string;
export type ActorId = string;
export type CreatedAt = string;
export type Id = string;
export type RequestId = string;
export type ResourceId = string | null;
export type ResourceType = string | null;
export type SubjectId = string | null;

export interface AuditResponse {
  action: Action;
  actor_id: ActorId;
  created_at: CreatedAt;
  id: Id;
  request_id: RequestId;
  resource_id: ResourceId;
  resource_type: ResourceType;
  subject_id: SubjectId;
}
