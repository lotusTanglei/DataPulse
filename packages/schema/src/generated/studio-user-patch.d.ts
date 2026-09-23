export type Active = boolean | null;
export type Password = string | null;
export type Role = "admin" | "editor" | "viewer";

export interface UserPatch {
  active?: Active;
  password?: Password;
  role?: Role | null;
}
