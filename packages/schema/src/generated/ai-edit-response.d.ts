/**
 * @minItems 1
 * @maxItems 8
 */
export type Commands =
  | [
      | AiUpdateFrameCommand
      | AiUpdatePropsCommand
      | AiUpdateStyleCommand
      | AiUpdateDataBindingCommand
      | AiSetComponentStateCommand
    ]
  | [
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      )
    ]
  | [
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      )
    ]
  | [
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      )
    ]
  | [
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      )
    ]
  | [
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      )
    ]
  | [
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      )
    ]
  | [
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      ),
      (
        | AiUpdateFrameCommand
        | AiUpdatePropsCommand
        | AiUpdateStyleCommand
        | AiUpdateDataBindingCommand
        | AiSetComponentStateCommand
      )
    ];
/**
 * @minItems 1
 * @maxItems 8
 */
export type ComponentIds =
  | [string]
  | [string, string]
  | [string, string, string]
  | [string, string, string, string]
  | [string, string, string, string, string]
  | [string, string, string, string, string, string]
  | [string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string];
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
export type Type = "update_frame";
export type ComponentId = string;
export type Type1 = "update_props";
export type ComponentId1 = string;
export type Type2 = "update_style";
export type ComponentId2 = string;
export type Type3 = "update_data_binding";
/**
 * @minItems 1
 * @maxItems 8
 */
export type ComponentIds1 =
  | [string]
  | [string, string]
  | [string, string, string]
  | [string, string, string, string]
  | [string, string, string, string, string]
  | [string, string, string, string, string, string]
  | [string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string];
export type Type4 = "set_component_state";
export type Explanation = string;
export type Warnings = string[];

export interface AiEditResponse {
  commands: Commands;
  explanation: Explanation;
  warnings?: Warnings;
}
export interface AiUpdateFrameCommand {
  component_ids: ComponentIds;
  patch: Patch;
  type?: Type;
}
export interface Patch {
  [k: string]: JsonValue;
}
export interface AiUpdatePropsCommand {
  component_id: ComponentId;
  patch: Patch1;
  type?: Type1;
}
export interface Patch1 {
  [k: string]: JsonValue;
}
export interface AiUpdateStyleCommand {
  component_id: ComponentId1;
  patch: Patch2;
  type?: Type2;
}
export interface Patch2 {
  [k: string]: JsonValue;
}
export interface AiUpdateDataBindingCommand {
  component_id: ComponentId2;
  data_binding: DataBinding;
  type?: Type3;
}
export interface DataBinding {
  [k: string]: JsonValue;
}
export interface AiSetComponentStateCommand {
  component_ids: ComponentIds1;
  patch: Patch3;
  type?: Type4;
}
export interface Patch3 {
  [k: string]: JsonValue;
}
