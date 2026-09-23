export type EmbedMessageEnvelope =
  | ReadyMessage
  | RefreshMessage
  | SetParametersMessage
  | GetParametersMessage
  | ParametersMessage
  | FullscreenMessage
  | AckMessage
  | DigitalHumanMessage
  | DigitalHumanStatusMessage
  | DigitalHumanEventMessage
  | ErrorMessage;
export type Capabilities = string[];
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
export type Action = "play" | "pause" | "stop" | "speak" | "getStatus" | "mute" | "setVolume";
export type ComponentId = string;
export type Enabled1 = boolean | null;
export type Volume = number | null;
export type InstanceId7 = string;
export type RequestId5 = string;
export type Type7 = "digitalHuman";
export type InstanceId8 = string;
export type RequestId6 = string;
export type Code = string | null;
export type ComponentId1 = string;
export type Muted = boolean;
export type Status =
  | "disabled"
  | "idle"
  | "loading_data"
  | "ready"
  | "queued"
  | "preparing_media"
  | "speaking"
  | "paused"
  | "muted"
  | "waiting_gesture"
  | "fallback"
  | "error";
export type Volume1 = number;
export type Type8 = "digitalHumanStatus";
export type Code1 = string | null;
export type ComponentId2 = string;
export type CueEnd = number | null;
export type CueIndex = number | null;
export type CueStart = number | null;
export type CueText = string | null;
export type Name =
  | "digitalHumanReady"
  | "statusChange"
  | "speechStart"
  | "speechEnd"
  | "speechError"
  | "fallback"
  | "userGestureRequired"
  | "subtitleCue";
export type Outcome = ("completed" | "stopped" | "cancelled") | null;
export type RequestId7 = string;
export type Source =
  | "initial"
  | "manual"
  | "interval"
  | "data_change"
  | "ranking_change"
  | "status_change"
  | "threshold"
  | "parameter"
  | "host";
export type Status1 =
  | "disabled"
  | "idle"
  | "loading_data"
  | "ready"
  | "queued"
  | "preparing_media"
  | "speaking"
  | "paused"
  | "muted"
  | "waiting_gesture"
  | "fallback"
  | "error";
export type TaskId = string | null;
export type Timestamp = number;
export type InstanceId9 = string;
export type Type9 = "digitalHumanEvent";
export type Code2 = string;
export type InstanceId10 = string;
export type Message = string;
export type RequestId8 = string | null;
export type Type10 = "error";

export interface ReadyMessage {
  capabilities?: Capabilities;
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
export interface DigitalHumanMessage {
  command: DigitalHumanCommand;
  instance_id: InstanceId7;
  request_id: RequestId5;
  type: Type7;
}
export interface DigitalHumanCommand {
  action: Action;
  component_id: ComponentId;
  enabled?: Enabled1;
  volume?: Volume;
}
export interface DigitalHumanStatusMessage {
  instance_id: InstanceId8;
  request_id: RequestId6;
  state: DigitalHumanState;
  type: Type8;
}
export interface DigitalHumanState {
  code: Code;
  component_id: ComponentId1;
  muted: Muted;
  status: Status;
  volume: Volume1;
}
export interface DigitalHumanEventMessage {
  event: DigitalHumanEvent;
  instance_id: InstanceId9;
  type: Type9;
}
export interface DigitalHumanEvent {
  code: Code1;
  component_id: ComponentId2;
  cue_end?: CueEnd;
  cue_index?: CueIndex;
  cue_start?: CueStart;
  cue_text?: CueText;
  name?: Name;
  outcome?: Outcome;
  request_id: RequestId7;
  source: Source;
  status: Status1;
  task_id: TaskId;
  timestamp: Timestamp;
}
export interface ErrorMessage {
  code: Code2;
  instance_id: InstanceId10;
  message: Message;
  request_id?: RequestId8;
  type: Type10;
}
