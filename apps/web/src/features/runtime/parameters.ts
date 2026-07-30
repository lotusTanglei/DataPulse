import type { DashboardDocument } from "../../contracts";
import type { JsonValue } from "../query/types";
import type { RuntimeParameters } from "./types";

type DashboardParameter = NonNullable<
  DashboardDocument["parameters"]
>[number];
export type ParameterMutationSource = "runtime" | "host";

export class ParameterValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ParameterValidationError";
  }
}

function isValidDate(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value));
}

function isValidDateTime(value: string): boolean {
  return !Number.isNaN(Date.parse(value));
}

function matchesType(parameter: DashboardParameter, value: JsonValue): boolean {
  if (value === null) {
    return true;
  }
  switch (parameter.data_type) {
    case "boolean":
      return typeof value === "boolean";
    case "integer":
      return typeof value === "number" && Number.isInteger(value);
    case "number":
      return typeof value === "number" && Number.isFinite(value);
    case "string":
      return typeof value === "string";
    case "date":
      return typeof value === "string" && isValidDate(value);
    case "datetime":
      return typeof value === "string" && isValidDateTime(value);
  }
}

function sameValue(first: JsonValue, second: JsonValue): boolean {
  return JSON.stringify(first) === JSON.stringify(second);
}

function validate(parameter: DashboardParameter, value: JsonValue): void {
  if (!matchesType(parameter, value)) {
    throw new ParameterValidationError(
      `Parameter "${parameter.name}" has an invalid ${parameter.data_type} value.`,
    );
  }
  if (
    parameter.allowed_values &&
    parameter.allowed_values.length > 0 &&
    !parameter.allowed_values.some((allowed) => sameValue(allowed, value))
  ) {
    throw new ParameterValidationError(
      `Parameter "${parameter.name}" is outside its allowed values.`,
    );
  }
}

export interface ParameterState {
  get(name: string): JsonValue;
  set(
    name: string,
    value: JsonValue,
    source?: ParameterMutationSource,
  ): void;
  values(): RuntimeParameters;
}

export function createParameterState(
  parameters: DashboardParameter[],
  initialValues: RuntimeParameters = {},
): ParameterState {
  const definitions = new Map(
    parameters.map((parameter) => [parameter.name, parameter]),
  );
  for (const name of Object.keys(initialValues)) {
    if (!definitions.has(name)) {
      throw new ParameterValidationError(`Unknown parameter: "${name}".`);
    }
  }

  const current: RuntimeParameters = {};
  for (const parameter of parameters) {
    const value =
      parameter.name in initialValues
        ? initialValues[parameter.name]!
        : (parameter.default ?? null);
    validate(parameter, value);
    current[parameter.name] = structuredClone(value);
  }

  function definition(name: string): DashboardParameter {
    const parameter = definitions.get(name);
    if (!parameter) {
      throw new ParameterValidationError(`Unknown parameter: "${name}".`);
    }
    return parameter;
  }

  return {
    get(name) {
      return structuredClone(current[definition(name).name]!);
    },
    set(name, value, source = "runtime") {
      const parameter = definition(name);
      if (source === "host" && !parameter.mutable) {
        throw new ParameterValidationError(
          `Parameter "${name}" cannot be changed by the host.`,
        );
      }
      validate(parameter, value);
      current[name] = structuredClone(value);
    },
    values() {
      return structuredClone(current);
    },
  };
}
