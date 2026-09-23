export type Password = string;
export type Username = string;

export interface UserCreate {
  password: Password;
  role?: "admin" | "editor" | "viewer";
  username: Username;
}
