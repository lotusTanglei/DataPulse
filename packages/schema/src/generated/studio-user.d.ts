export type Active = boolean;
export type CreatedAt = string;
export type Id = string;
export type Role = "admin" | "editor" | "viewer";
export type UpdatedAt = string;
export type Username = string;

export interface UserResponse {
  active: Active;
  created_at: CreatedAt;
  id: Id;
  role: Role;
  updated_at: UpdatedAt;
  username: Username;
}
