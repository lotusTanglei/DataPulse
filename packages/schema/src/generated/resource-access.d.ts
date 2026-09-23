export type Manage = boolean;
export type Publish = boolean;
export type Read = boolean;
export type Write = boolean;

export interface ResourceAccessResponse {
  manage: Manage;
  publish: Publish;
  read: Read;
  write: Write;
}
