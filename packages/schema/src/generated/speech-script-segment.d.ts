export type DurationMs = number;
export type Kind = "paragraph" | "pause" | "emphasis";
export type Text = string;

export interface SpeechScriptSegment {
  duration_ms?: DurationMs;
  kind?: Kind;
  text?: Text;
}
