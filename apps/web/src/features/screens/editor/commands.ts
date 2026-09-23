import type { DashboardDocument } from "../../../contracts";

export type ComponentInstance = NonNullable<
  DashboardDocument["components"]
>[number];
export type ComponentFrame = ComponentInstance["frame"];
export type DashboardParameter = NonNullable<
  DashboardDocument["parameters"]
>[number];

type ComponentState = NonNullable<ComponentInstance["state"]>;
type ComponentProps = NonNullable<ComponentInstance["props"]>;
type ComponentStyle = NonNullable<ComponentInstance["style"]>;
type Canvas = DashboardDocument["canvas"];
type Theme = NonNullable<DashboardDocument["theme"]>;
type Refresh = NonNullable<DashboardDocument["refresh"]>;

export interface DigitalHumanCopyOptions {
  copySpeech?: boolean;
  copyTrigger?: boolean;
  copyAudio?: boolean;
}

export type EditorCommand =
  | { type: "batch"; commands: EditorCommand[] }
  | { type: "add_component"; component: ComponentInstance }
  | { type: "add_plugin_component"; component: ComponentInstance; dependency: { id: string; version: string } }
  | { type: "migrate_plugin"; expected_document: string; dependency: { id: string; version: string }; from_version: string; properties: Record<string, ComponentProps> }
  | {
      type: "group_components";
      component_ids: string[];
      group_id: string;
    }
  | { type: "ungroup_components"; component_ids: string[] }
  | {
      type: "replace_component";
      component_id: string;
      component: ComponentInstance;
    }
  | { type: "remove_components"; component_ids: string[] }
  | {
      type: "duplicate_components";
      source_ids: string[];
      id_map: Record<string, string>;
      offset?: { x: number; y: number };
      digital_human?: DigitalHumanCopyOptions;
    }
  | {
      type: "update_frame";
      component_ids: string[];
      patch: Partial<ComponentFrame>;
    }
  | {
      type: "update_frames";
      patches: Record<string, Partial<ComponentFrame>>;
    }
  | {
      type: "update_props";
      component_id: string;
      patch: ComponentProps;
    }
  | {
      type: "update_style";
      component_id: string;
      patch: ComponentStyle;
    }
  | {
      type: "update_data_binding";
      component_id: string;
      data_binding: NonNullable<ComponentInstance["data_binding"]>;
    }
  | {
      type: "update_interactions";
      component_id: string;
      interactions: NonNullable<ComponentInstance["interactions"]>;
    }
  | {
      type: "set_component_state";
      component_ids: string[];
      patch: Partial<ComponentState>;
    }
  | { type: "reorder_components"; component_ids: string[] }
  | { type: "update_canvas"; patch: Partial<Canvas> }
  | { type: "update_theme"; patch: Partial<Theme> }
  | { type: "update_refresh"; refresh: Refresh }
  | { type: "set_parameters"; parameters: DashboardParameter[] };

export class EditorCommandError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "EditorCommandError";
  }
}

function components(document: DashboardDocument): ComponentInstance[] {
  return document.components ?? [];
}

function assertKnownIds(
  document: DashboardDocument,
  componentIds: string[],
): void {
  const known = new Set(components(document).map((component) => component.id));
  const missing = componentIds.filter((id) => !known.has(id));
  if (missing.length > 0) {
    throw new EditorCommandError(`Unknown component IDs: ${missing.join(", ")}`);
  }
}

function patchComponents(
  document: DashboardDocument,
  componentIds: string[],
  patch: (component: ComponentInstance) => ComponentInstance,
): ComponentInstance[] {
  assertKnownIds(document, componentIds);
  const selected = new Set(componentIds);
  return components(document).map((component) =>
    selected.has(component.id) ? patch(component) : component,
  );
}

function applyDigitalHumanCopyOptions(
  component: ComponentInstance,
  options: DigitalHumanCopyOptions | undefined,
): ComponentInstance {
  if (component.type !== "builtin.digital_human" || !options) return component;
  const props = { ...(component.props ?? {}) } as ComponentProps;
  let dataBinding = component.data_binding;
  if (options.copySpeech === false) {
    delete props.speech_template;
    dataBinding = {};
  }
  if (options.copyTrigger === false) {
    delete props.trigger;
    props.auto_play = false;
  }
  if (options.copyAudio === false) {
    delete props.audio_asset_id;
    delete props.recording;
    delete props.recordings;
    if (props.speech_source === "audio") props.speech_source = "browser";
  }
  return { ...component, props, data_binding: structuredClone(dataBinding) };
}

function remapDigitalHumanReferences(
  component: ComponentInstance,
  idMap: Record<string, string>,
  options: DigitalHumanCopyOptions | undefined,
): ComponentInstance {
  if (
    component.type !== "builtin.digital_human" ||
    options?.copySpeech === false ||
    component.data_binding?.source !== "components"
  ) {
    return component;
  }
  const binding = component.data_binding as Record<string, unknown>;
  if (!Array.isArray(binding.variables)) return component;
  return {
    ...component,
    data_binding: {
      ...binding,
      variables: binding.variables.map((variable) => {
        if (!variable || typeof variable !== "object" || Array.isArray(variable)) {
          return variable;
        }
        const item = variable as Record<string, unknown>;
        const componentId = item.component_id;
        return {
          ...item,
          component_id:
            typeof componentId === "string"
              ? idMap[componentId] ?? componentId
              : componentId,
        };
      }),
    },
  };
}

export function applyCommand(
  document: DashboardDocument,
  command: EditorCommand,
): DashboardDocument {
  const next = structuredClone(document);
  switch (command.type) {
    case "migrate_plugin": {
      const pinned = next.plugin_dependencies?.find((item) => item.id === command.dependency.id);
      if (JSON.stringify(document) !== command.expected_document || pinned?.version !== command.from_version) {
        throw new EditorCommandError("草稿已变化，请重新执行版本切换。");
      }
      const ids = Object.keys(command.properties);
      next.components = patchComponents(next, ids, (component) => ({
        ...component, props: structuredClone(command.properties[component.id]!),
      }));
      pinned.version = command.dependency.version;
      break;
    }
    case "add_plugin_component": {
      const dependencies = next.plugin_dependencies ?? [];
      const pinned = dependencies.find((item) => item.id === command.dependency.id);
      if (pinned && pinned.version !== command.dependency.version) {
        throw new EditorCommandError("A different plugin version is already pinned to this draft.");
      }
      if (!pinned) next.plugin_dependencies = [...dependencies, structuredClone(command.dependency)];
      return applyCommand(next, { type: "add_component", component: command.component });
    }
    case "batch": {
      let nextDocument = next;
      for (const nested of command.commands) {
        nextDocument = applyCommand(nextDocument, nested);
      }
      return nextDocument;
    }
    case "add_component": {
      if (
        components(next).some(
          (component) => component.id === command.component.id,
        )
      ) {
        throw new EditorCommandError(
          `Duplicate component ID: ${command.component.id}`,
        );
      }
      next.components = [...components(next), structuredClone(command.component)];
      break;
    }
    case "group_components": {
      if (command.component_ids.length < 2) {
        throw new EditorCommandError("A group must contain at least two components.");
      }
      assertKnownIds(next, command.component_ids);
      next.components = patchComponents(
        next,
        command.component_ids,
        (component) => ({
          ...component,
          state: { ...(component.state ?? {}), group_id: command.group_id },
        }),
      );
      break;
    }
    case "ungroup_components":
      assertKnownIds(next, command.component_ids);
      next.components = patchComponents(
        next,
        command.component_ids,
        (component) => {
          const state = { ...(component.state ?? {}) };
          delete state.group_id;
          return { ...component, state };
        },
      );
      break;
    case "replace_component":
      if (command.component.id !== command.component_id) {
        throw new EditorCommandError(
          `Replacement component ID mismatch: ${command.component_id}`,
        );
      }
      next.components = patchComponents(
        next,
        [command.component_id],
        () => structuredClone(command.component),
      );
      break;
    case "remove_components": {
      assertKnownIds(next, command.component_ids);
      const removed = new Set(command.component_ids);
      next.components = components(next).filter(
        (component) => !removed.has(component.id),
      );
      break;
    }
    case "duplicate_components": {
      assertKnownIds(next, command.source_ids);
      const existing = new Set(
        components(next).map((component) => component.id),
      );
      const offset = command.offset ?? { x: 20, y: 20 };
      const copies = command.source_ids.map((sourceId) => {
        const newId = command.id_map[sourceId];
        if (!newId || existing.has(newId)) {
          throw new EditorCommandError(
            `Missing or duplicate copied component ID for: ${sourceId}`,
          );
        }
        existing.add(newId);
        const source = components(next).find(
          (component) => component.id === sourceId,
        )!;
        const copied = applyDigitalHumanCopyOptions(
          structuredClone(source),
          command.digital_human,
        );
        const remapped = remapDigitalHumanReferences(
          copied,
          command.id_map,
          command.digital_human,
        );
        return {
          ...remapped,
          id: newId,
          frame: {
            ...remapped.frame,
            x: source.frame.x + offset.x,
            y: source.frame.y + offset.y,
          },
        };
      });
      next.components = [...components(next), ...copies];
      break;
    }
    case "update_frame":
      next.components = patchComponents(
        next,
        command.component_ids,
        (component) => ({
          ...component,
          frame: { ...component.frame, ...command.patch },
        }),
      );
      break;
    case "update_frames": {
      const ids = Object.keys(command.patches);
      next.components = patchComponents(next, ids, (component) => ({
        ...component,
        frame: {
          ...component.frame,
          ...command.patches[component.id],
        },
      }));
      break;
    }
    case "update_props":
      next.components = patchComponents(
        next,
        [command.component_id],
        (component) => ({
          ...component,
          props: { ...(component.props ?? {}), ...command.patch },
        }),
      );
      break;
    case "update_style":
      next.components = patchComponents(
        next,
        [command.component_id],
        (component) => ({
          ...component,
          style: { ...(component.style ?? {}), ...command.patch },
        }),
      );
      break;
    case "update_data_binding":
      next.components = patchComponents(
        next,
        [command.component_id],
        (component) => ({
          ...component,
          data_binding: structuredClone(command.data_binding),
        }),
      );
      break;
    case "update_interactions":
      next.components = patchComponents(
        next,
        [command.component_id],
        (component) => ({
          ...component,
          interactions: structuredClone(command.interactions),
        }),
      );
      break;
    case "set_component_state":
      next.components = patchComponents(
        next,
        command.component_ids,
        (component) => ({
          ...component,
          state: { ...(component.state ?? {}), ...command.patch },
        }),
      );
      break;
    case "reorder_components": {
      const current = components(next);
      assertKnownIds(next, command.component_ids);
      if (
        command.component_ids.length !== current.length ||
        new Set(command.component_ids).size !== current.length
      ) {
        throw new EditorCommandError(
          "Reorder command must contain every component exactly once.",
        );
      }
      const byId = new Map(current.map((component) => [component.id, component]));
      next.components = command.component_ids.map((id, index) => {
        const component = byId.get(id)!;
        return {
          ...component,
          frame: { ...component.frame, z_index: index },
        };
      });
      break;
    }
    case "update_canvas":
      next.canvas = { ...next.canvas, ...command.patch };
      break;
    case "update_theme":
      next.theme = { ...(next.theme ?? {}), ...command.patch };
      break;
    case "update_refresh":
      next.refresh = structuredClone(command.refresh);
      break;
    case "set_parameters":
      next.parameters = structuredClone(command.parameters);
      break;
  }
  return next;
}
