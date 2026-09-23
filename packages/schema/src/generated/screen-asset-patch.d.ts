export type LicenseExpiresAt = string | null;
export type LicenseNote = string | null;
export type Name = string | null;

export interface ScreenAssetPatch {
  license_expires_at?: LicenseExpiresAt;
  license_note?: LicenseNote;
  name?: Name;
}
