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
