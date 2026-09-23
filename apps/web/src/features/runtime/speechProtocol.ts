import type { DigitalHumanStatus, SpeechSource } from "./builtins/digitalHuman";

export interface SpeechCommand {
  component_id: string;
  action: "play" | "pause" | "stop" | "speak" | "mute" | "setVolume" | "getStatus";
  enabled?: boolean;
  volume?: number;
}

export interface SpeechStatus {
  component_id: string;
  status: DigitalHumanStatus;
  code: string | null;
  muted: boolean;
  volume: number;
}

export interface SpeechEvent {
  name: "digitalHumanReady" | "statusChange" | "speechStart" | "speechEnd" | "speechError" | "fallback" | "userGestureRequired" | "subtitleCue";
  outcome?: "completed" | "stopped" | "cancelled";
  component_id: string;
  task_id: string | null;
  status: DigitalHumanStatus;
  source: SpeechSource;
  code: string | null;
  request_id: string;
  timestamp: number;
  cue_index?: number | null;
  cue_text?: string | null;
  cue_start?: number | null;
  cue_end?: number | null;
}

export interface SpeechController {
  play(source?: SpeechSource): void;
  pause(): void;
  stop(): void;
  speak(source?: SpeechSource): void;
  mute(value: boolean): void;
  setVolume(value: number): void;
  getStatus(): SpeechStatus;
}

export function isSpeechCommand(value: unknown): value is SpeechCommand {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const command = value as Record<string, unknown>;
  if (Object.keys(command).some((key) => !["component_id", "action", "enabled", "volume"].includes(key))) return false;
  if (typeof command.component_id !== "string" || !command.component_id.trim() || typeof command.action !== "string") return false;
  if (command.action === "mute") return typeof command.enabled === "boolean" && command.volume === undefined;
  if (command.action === "setVolume") return command.enabled === undefined && typeof command.volume === "number" && Number.isFinite(command.volume) && command.volume >= 0 && command.volume <= 1;
  return ["play", "pause", "stop", "speak", "getStatus"].includes(command.action) && command.enabled === undefined && command.volume === undefined;
}
