import type { DashboardDocument } from "../../contracts";

export const CURRENT_COMPONENT_CONTRACT_VERSION = "1.0.0";

function versionedRecord(value: unknown, kind: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`Invalid ${kind} payload.`);
  }
  const payload = structuredClone(value) as Record<string, unknown>;
  const version = payload.schema_version ?? 0;
  if (version !== 0 && version !== 1) {
    throw new Error(`Unsupported ${kind} schema version: ${String(version)}`);
  }
  payload.schema_version = 1;
  return payload;
}

export function migrateTemplateDocument(value: unknown): DashboardDocument {
  const document = versionedRecord(value, "dashboard document");
  const components = document.components ?? [];
  if (!Array.isArray(components)) {
    throw new Error("Invalid dashboard document components.");
  }
  document.components = components.map((component) => {
    const migrated = versionedRecord(component, "component");
    const contractVersion = migrated.contract_version
      ?? CURRENT_COMPONENT_CONTRACT_VERSION;
    if (contractVersion !== CURRENT_COMPONENT_CONTRACT_VERSION) {
      throw new Error(
        `Unsupported component contract version: ${String(contractVersion)}`,
      );
    }
    migrated.contract_version = CURRENT_COMPONENT_CONTRACT_VERSION;
    return migrated;
  });
  return document as unknown as DashboardDocument;
}
