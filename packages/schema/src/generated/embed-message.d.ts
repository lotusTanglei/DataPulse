export type EmbedMessageEnvelope =
  | ReadyMessage
  | RefreshMessage
  | SetParametersMessage
  | GetParametersMessage
  | FullscreenMessage
  | ExportImageMessage
  | ErrorMessage
  | AiQuestionMessage;
export type Type = "ready";
export type Type1 = "refresh";
export type JsonValue = unknown;
export type RequestId = string;
export type Type2 = "setParameters";
export type RequestId1 = string;
export type Type3 = "getParameters";
export type Enabled = boolean;
export type RequestId2 = string;
export type Type4 = "fullscreen";
export type Format = "png" | "jpeg";
export type RequestId3 = string;
export type Type5 = "exportImage";
export type Code = string;
export type Message = string;
export type RequestId4 = string | null;
export type Type6 = "error";
export type Question = string;
export type RequestId5 = string;
export type Type7 = "aiQuestion";

export interface ReadyMessage {
  type: Type;
}
export interface RefreshMessage {
  type: Type1;
}
export interface SetParametersMessage {
  parameters: Parameters;
  request_id: RequestId;
  type: Type2;
}
export interface Parameters {
  [k: string]: JsonValue;
}
export interface GetParametersMessage {
  request_id: RequestId1;
  type: Type3;
}
export interface FullscreenMessage {
  enabled: Enabled;
  request_id: RequestId2;
  type: Type4;
}
export interface ExportImageMessage {
  format?: Format;
  request_id: RequestId3;
  type: Type5;
}
export interface ErrorMessage {
  code: Code;
  message: Message;
  request_id?: RequestId4;
  type: Type6;
}
export interface AiQuestionMessage {
  question: Question;
  request_id: RequestId5;
  type: Type7;
}
