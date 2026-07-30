export type AllowedOrigin = string;
export type Audience = string;
export type ExpiresAt = string;
export type IssuedAt = string;
export type Issuer = string;
export type MutableParameters = string[];
export type JsonValue =
  | JsonValue[]
  | {
      [k: string]: JsonValue;
    }
  | string
  | boolean
  | number
  | null;
export type SchemaVersion = 1;
export type ScreenId = string;
export type TicketId = string;

export interface EmbedTicketClaims {
  allowed_origin: AllowedOrigin;
  audience?: Audience;
  expires_at: ExpiresAt;
  issued_at: IssuedAt;
  issuer?: Issuer;
  mutable_parameters?: MutableParameters;
  parameters?: Parameters;
  schema_version?: SchemaVersion;
  screen_id: ScreenId;
  ticket_id: TicketId;
}
export interface Parameters {
  [k: string]: JsonValue;
}
