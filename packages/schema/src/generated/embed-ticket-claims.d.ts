export type AiEnabled = boolean;
export type AllowedOrigin = string;
export type Audience = string;
export type DashboardId = string;
export type ExpiresAt = string;
export type IssuedAt = string;
export type Issuer = string;
export type JsonValue = unknown;
export type PublishedVersionId = string;
export type SchemaVersion = 1;

export interface EmbedTicketClaims {
  ai_enabled?: AiEnabled;
  allowed_origin: AllowedOrigin;
  audience?: Audience;
  dashboard_id: DashboardId;
  expires_at: ExpiresAt;
  issued_at: IssuedAt;
  issuer?: Issuer;
  parameters?: Parameters;
  published_version_id: PublishedVersionId;
  schema_version?: SchemaVersion;
}
export interface Parameters {
  [k: string]: JsonValue;
}
