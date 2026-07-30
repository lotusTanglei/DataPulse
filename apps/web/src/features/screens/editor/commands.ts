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

export type EditorCommand =
  | { type: "add_component"; component: ComponentInstance }
  | { type: "remove_components"; component_ids: string[] }
  | {
      type: "duplicate_components";
      source_ids: string[];
      id_map: Record<string, string>;
      offset?: { x: number; y: number };
    }
  | {
      type: "update_frame";
      component_ids: string[];
      patch: Partial<ComponentFrame>;
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

export function applyCommand(
  document: DashboardDocument,
  command: EditorCommand,
): DashboardDocument {
  const next = structuredClone(document);
  switch (command.type) {
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
        return {
          ...structuredClone(source),
          id: newId,
          frame: {
            ...source.frame,
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
