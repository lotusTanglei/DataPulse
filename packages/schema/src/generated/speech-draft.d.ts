export type PreviewOnly = true;
export type Text = string;
export type Warnings = string[];

export interface SpeechDraftResponse {
  preview_only?: PreviewOnly;
  text: Text;
  warnings?: Warnings;
}
