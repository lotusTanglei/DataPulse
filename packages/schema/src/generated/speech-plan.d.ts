export type ComponentId = string;
export type ContentHash = string;
export type CreatedAt = string;
export type Id = string;
export type Language = string;
export type Pitch = number;
export type ProviderId = string;
export type ProviderVersion = string;
export type Rate = number;
export type ScreenId = string;
export type Text = string;
export type Voice = string;
export type Volume = number;

export interface SpeechPlanResponse {
  component_id: ComponentId;
  content_hash: ContentHash;
  created_at: CreatedAt;
  id: Id;
  language: Language;
  pitch?: Pitch;
  provider_id: ProviderId;
  provider_version: ProviderVersion;
  rate?: Rate;
  screen_id: ScreenId;
  text: Text;
  voice: Voice;
  volume?: Volume;
}
