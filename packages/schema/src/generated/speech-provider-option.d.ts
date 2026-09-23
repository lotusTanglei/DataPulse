export type DefaultVoice = string;
export type Id = string;
export type Language = string;
export type Name = string;

export interface SpeechProviderOption {
  default_voice: DefaultVoice;
  id: Id;
  language: Language;
  name: Name;
}
