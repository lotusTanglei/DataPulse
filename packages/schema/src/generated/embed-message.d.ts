export type EmbedMessageEnvelope =
  | ReadyMessage
  | RefreshMessage
  | SetParametersMessage
  | GetParametersMessage
  | ParametersMessage
  | FullscreenMessage
  | AckMessage
  | ErrorMessage;
export type InstanceId = string;
export type ProtocolVersion = 1;
export type Type = "ready";
export type InstanceId1 = string;
export type Type1 = "refresh";
export type InstanceId2 = string;
export type JsonValue =
  | JsonValue[]
  | {
      [k: string]: JsonValue;
    }
  | string
  | boolean
  | number
  | null;
export type RequestId = string;
export type Type2 = "setParameters";
export type InstanceId3 = string;
export type RequestId1 = string;
export type Type3 = "getParameters";
export type InstanceId4 = string;
export type RequestId2 = string;
export type Type4 = "parameters";
export type Enabled = boolean;
export type InstanceId5 = string;
export type RequestId3 = string;
export type Type5 = "fullscreen";
export type InstanceId6 = string;
export type RequestId4 = string;
export type Type6 = "ack";
export type Code = string;
export type InstanceId7 = string;
export type Message = string;
export type RequestId5 = string | null;
export type Type7 = "error";

export interface ReadyMessage {
  instance_id: InstanceId;
  protocol_version?: ProtocolVersion;
  type: Type;
}
export interface RefreshMessage {
  instance_id: InstanceId1;
  type: Type1;
}
export interface SetParametersMessage {
  instance_id: InstanceId2;
  parameters: Parameters;
  request_id: RequestId;
  type: Type2;
}
export interface Parameters {
  [k: string]: JsonValue;
}
export interface GetParametersMessage {
  instance_id: InstanceId3;
  request_id: RequestId1;
  type: Type3;
}
export interface ParametersMessage {
  instance_id: InstanceId4;
  parameters: Parameters1;
  request_id: RequestId2;
  type: Type4;
}
export interface Parameters1 {
  [k: string]: JsonValue;
}
export interface FullscreenMessage {
  enabled: Enabled;
  instance_id: InstanceId5;
  request_id: RequestId3;
  type: Type5;
}
export interface AckMessage {
  instance_id: InstanceId6;
  request_id: RequestId4;
  type: Type6;
}
export interface ErrorMessage {
  code: Code;
  instance_id: InstanceId7;
  message: Message;
  request_id?: RequestId5;
  type: Type7;
}
