export type InDraft = boolean;
export type InPublished = boolean;
export type ScreenId = string;
export type ScreenName = string;

export interface ScreenAssetReference {
  in_draft: InDraft;
  in_published: InPublished;
  screen_id: ScreenId;
  screen_name: ScreenName;
}
