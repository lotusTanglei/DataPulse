/** Trusted same-origin plugins: lifecycle isolation is not a security sandbox. */
export type JsonValue =
  null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };
export interface PluginQueryResult {
  columns: ReadonlyArray<{ name: string; data_type: string }>;
  rows: ReadonlyArray<ReadonlyArray<JsonValue>>;
  row_count: number;
  truncated: boolean;
  duration_ms: number;
  request_id: string;
}
export interface PluginContext {
  instanceId: string;
  props: Readonly<Record<string, JsonValue>>;
  result: PluginQueryResult | null;
  loading: boolean;
  error: unknown;
  theme: Readonly<Record<string, JsonValue>>;
  signal: AbortSignal;
}
export interface PluginHandle {
  update(context: PluginContext): void;
  destroy(): void;
}
export interface PluginComponent {
  mount(element: HTMLElement, context: PluginContext): PluginHandle;
  /** Invoked only by an explicit draft migration; never upgrades a publication. */
  migrate?(
    props: Record<string, JsonValue>,
    fromVersion: string,
  ): Record<string, JsonValue>;
}
export interface PluginDefinition {
  apiVersion: 1;
  components: Record<string, PluginComponent>;
}
export function definePlugin<T extends PluginDefinition>(definition: T): T {
  return definition;
}
