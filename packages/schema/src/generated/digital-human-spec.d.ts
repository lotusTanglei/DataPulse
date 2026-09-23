/**
 * @maxItems 8
 */
export type Actions =
  | []
  | [DigitalHumanAction]
  | [DigitalHumanAction, DigitalHumanAction]
  | [DigitalHumanAction, DigitalHumanAction, DigitalHumanAction]
  | [DigitalHumanAction, DigitalHumanAction, DigitalHumanAction, DigitalHumanAction]
  | [DigitalHumanAction, DigitalHumanAction, DigitalHumanAction, DigitalHumanAction, DigitalHumanAction]
  | [
      DigitalHumanAction,
      DigitalHumanAction,
      DigitalHumanAction,
      DigitalHumanAction,
      DigitalHumanAction,
      DigitalHumanAction
    ]
  | [
      DigitalHumanAction,
      DigitalHumanAction,
      DigitalHumanAction,
      DigitalHumanAction,
      DigitalHumanAction,
      DigitalHumanAction,
      DigitalHumanAction
    ]
  | [
      DigitalHumanAction,
      DigitalHumanAction,
      DigitalHumanAction,
      DigitalHumanAction,
      DigitalHumanAction,
      DigitalHumanAction,
      DigitalHumanAction,
      DigitalHumanAction
    ];
export type AssetId = string;
export type AssetKind = "image" | "video";
export type ConditionMode = "all" | "any";
/**
 * @maxItems 20
 */
export type Conditions =
  | []
  | [DigitalHumanCondition]
  | [DigitalHumanCondition, DigitalHumanCondition]
  | [DigitalHumanCondition, DigitalHumanCondition, DigitalHumanCondition]
  | [DigitalHumanCondition, DigitalHumanCondition, DigitalHumanCondition, DigitalHumanCondition]
  | [DigitalHumanCondition, DigitalHumanCondition, DigitalHumanCondition, DigitalHumanCondition, DigitalHumanCondition]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ];
export type Operator = "gt" | "gte" | "lt" | "lte" | "eq" | "neq" | "exists";
export type JsonValue =
  | JsonValue[]
  | {
      [k: string]: JsonValue;
    }
  | string
  | boolean
  | number
  | number
  | null;
export type Variable = string;
export type DurationMs = number;
export type Id = string;
export type Kind = "nod" | "wave" | "emphasis";
export type Priority = number;
export type Animation = boolean;
export type AudioAssetId = string;
export type AutoPlay = boolean;
export type AvatarAssetId = string;
export type AvatarKind = "image" | "video";
export type DailyMaxCount = number;
export type DailyMaxSeconds = number;
export type EmptyText = string;
export type Enabled = boolean;
export type ErrorText = string;
export type Fit = "contain" | "cover" | "none";
export type Language = string;
export type MaxDurationSeconds = number;
export type MaxQueueLength = number;
export type Mirror = boolean;
export type MissingText = string;
export type Muted = boolean;
export type Name = string;
export type Pitch = number;
export type QueuePolicy = "queue" | "merge" | "drop_old" | "interrupt";
export type QuietEnd = string | null;
export type QuietMode = "mute" | "delay" | "subtitle";
export type QuietStart = string | null;
export type Rate = number;
export type AssetId1 = string;
export type ConditionMode1 = "all" | "any";
/**
 * @maxItems 20
 */
export type Conditions1 =
  | []
  | [DigitalHumanCondition]
  | [DigitalHumanCondition, DigitalHumanCondition]
  | [DigitalHumanCondition, DigitalHumanCondition, DigitalHumanCondition]
  | [DigitalHumanCondition, DigitalHumanCondition, DigitalHumanCondition, DigitalHumanCondition]
  | [DigitalHumanCondition, DigitalHumanCondition, DigitalHumanCondition, DigitalHumanCondition, DigitalHumanCondition]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ];
export type End = number;
export type Start = number;
export type Text = string;
/**
 * @maxItems 500
 */
export type Cues = SubtitleCue[];
export type DurationSeconds = number;
export type Priority1 = number;
export type Sha256 = string;
export type SubtitleAssetId = string;
export type SubtitleSha256 = string;
export type Transcript = string;
/**
 * @maxItems 20
 */
export type Recordings =
  | []
  | [SpeechRecording]
  | [SpeechRecording, SpeechRecording]
  | [SpeechRecording, SpeechRecording, SpeechRecording]
  | [SpeechRecording, SpeechRecording, SpeechRecording, SpeechRecording]
  | [SpeechRecording, SpeechRecording, SpeechRecording, SpeechRecording, SpeechRecording]
  | [SpeechRecording, SpeechRecording, SpeechRecording, SpeechRecording, SpeechRecording, SpeechRecording]
  | [
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording
    ]
  | [
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording
    ]
  | [
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording
    ]
  | [
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording
    ]
  | [
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording
    ]
  | [
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording
    ]
  | [
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording
    ]
  | [
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording
    ]
  | [
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording
    ]
  | [
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording
    ]
  | [
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording
    ]
  | [
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording
    ]
  | [
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording
    ]
  | [
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording,
      SpeechRecording
    ];
export type Role = string;
export type SchemaVersion = 1;
export type ShowControls = boolean;
export type ShowIdentity = boolean;
export type ShowStatus = boolean;
export type SpeakingAssetId = string;
export type SpeakingKind = "image" | "video";
export type DurationMs1 = number;
export type Kind1 = "paragraph" | "pause" | "emphasis";
export type Text1 = string;
/**
 * @maxItems 50
 */
export type SpeechSegments = SpeechScriptSegment[];
export type SpeechSource = "auto" | "browser" | "audio" | "video";
export type SpeechTemplate = string;
export type StaleAfterSeconds = number;
export type StaleText = string;
export type SubtitleBackground = string;
export type SubtitleColor = string;
export type SubtitleEnabled = boolean;
export type SubtitleFontSize = number;
export type SubtitleMaxLines = number;
export type SubtitlePosition = "top" | "bottom";
export type SubtitleScroll = "wrap" | "scroll";
export type TaskTtlSeconds = number;
export type Timezone = string;
export type ConditionMode2 = "all" | "any";
/**
 * @maxItems 20
 */
export type Conditions2 =
  | []
  | [DigitalHumanCondition]
  | [DigitalHumanCondition, DigitalHumanCondition]
  | [DigitalHumanCondition, DigitalHumanCondition, DigitalHumanCondition]
  | [DigitalHumanCondition, DigitalHumanCondition, DigitalHumanCondition, DigitalHumanCondition]
  | [DigitalHumanCondition, DigitalHumanCondition, DigitalHumanCondition, DigitalHumanCondition, DigitalHumanCondition]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ]
  | [
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition,
      DigitalHumanCondition
    ];
export type CooldownSeconds = number;
export type DebounceSeconds = number;
export type Direction = "above" | "below";
export type Edge = "enter" | "recover" | "both";
export type IncludeHost = boolean;
export type IntervalSeconds = number | null;
export type Kind2 =
  "initial" | "manual" | "interval" | "data_change" | "ranking_change" | "status_change" | "threshold" | "parameter";
export type MinChange = number;
export type Parameter = string | null;
export type Priority2 = number;
export type Threshold = number | null;
export type Variable1 = string | null;
export type WindowEnd = string | null;
export type WindowStart = string | null;
export type VoiceEnabled = boolean;
export type Volume = number;

export interface DigitalHumanSpec {
  actions?: Actions;
  animation?: Animation;
  audio_asset_id?: AudioAssetId;
  auto_play?: AutoPlay;
  avatar_asset_id?: AvatarAssetId;
  avatar_kind?: AvatarKind;
  daily_max_count?: DailyMaxCount;
  daily_max_seconds?: DailyMaxSeconds;
  empty_text?: EmptyText;
  enabled?: Enabled;
  error_text?: ErrorText;
  fit?: Fit;
  language?: Language;
  max_duration_seconds?: MaxDurationSeconds;
  max_queue_length?: MaxQueueLength;
  mirror?: Mirror;
  missing_text?: MissingText;
  muted?: Muted;
  name?: Name;
  pitch?: Pitch;
  queue_policy?: QueuePolicy;
  quiet_end?: QuietEnd;
  quiet_mode?: QuietMode;
  quiet_start?: QuietStart;
  rate?: Rate;
  recording?: SpeechRecording | null;
  recordings?: Recordings;
  role?: Role;
  schema_version?: SchemaVersion;
  show_controls?: ShowControls;
  show_identity?: ShowIdentity;
  show_status?: ShowStatus;
  speaking_asset_id?: SpeakingAssetId;
  speaking_kind?: SpeakingKind;
  speech_segments?: SpeechSegments;
  speech_source?: SpeechSource;
  speech_template?: SpeechTemplate;
  stale_after_seconds?: StaleAfterSeconds;
  stale_text?: StaleText;
  subtitle_background?: SubtitleBackground;
  subtitle_color?: SubtitleColor;
  subtitle_enabled?: SubtitleEnabled;
  subtitle_font_size?: SubtitleFontSize;
  subtitle_max_lines?: SubtitleMaxLines;
  subtitle_position?: SubtitlePosition;
  subtitle_scroll?: SubtitleScroll;
  task_ttl_seconds?: TaskTtlSeconds;
  timezone?: Timezone;
  trigger?: DigitalHumanTrigger;
  voice_enabled?: VoiceEnabled;
  volume?: Volume;
}
export interface DigitalHumanAction {
  asset_id: AssetId;
  asset_kind?: AssetKind;
  condition_mode?: ConditionMode;
  conditions?: Conditions;
  duration_ms?: DurationMs;
  id: Id;
  kind?: Kind;
  priority?: Priority;
}
export interface DigitalHumanCondition {
  operator?: Operator;
  value?:
    | JsonValue[]
    | {
        [k: string]: JsonValue;
      }
    | string
    | boolean
    | number
    | number
    | null;
  variable: Variable;
}
export interface SpeechRecording {
  asset_id: AssetId1;
  condition_mode?: ConditionMode1;
  conditions?: Conditions1;
  cues?: Cues;
  duration_seconds: DurationSeconds;
  priority?: Priority1;
  sha256: Sha256;
  subtitle_asset_id?: SubtitleAssetId;
  subtitle_sha256?: SubtitleSha256;
  transcript: Transcript;
}
export interface SubtitleCue {
  end: End;
  start: Start;
  text: Text;
}
export interface SpeechScriptSegment {
  duration_ms?: DurationMs1;
  kind?: Kind1;
  text?: Text1;
}
export interface DigitalHumanTrigger {
  condition_mode?: ConditionMode2;
  conditions?: Conditions2;
  cooldown_seconds?: CooldownSeconds;
  debounce_seconds?: DebounceSeconds;
  direction?: Direction;
  edge?: Edge;
  include_host?: IncludeHost;
  interval_seconds?: IntervalSeconds;
  kind?: Kind2;
  min_change?: MinChange;
  parameter?: Parameter;
  priority?: Priority2;
  threshold?: Threshold;
  variable?: Variable1;
  window_end?: WindowEnd;
  window_start?: WindowStart;
}
