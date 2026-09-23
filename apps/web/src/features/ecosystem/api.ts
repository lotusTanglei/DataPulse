import { apiRequest } from "../../lib/api";
import type { Screen } from "../screens/types";
import { importPluginResponse } from "./plugins";
import type { CatalogPackage, PluginPackage, TemplateApply } from "./types";

const root = "/api/admin/ecosystem/packages";
export function packagePath(
  item: Pick<CatalogPackage, "kind" | "id" | "version">,
): string {
  return `${root}/${item.kind}/${encodeURIComponent(item.id)}/${encodeURIComponent(item.version)}`;
}
export function listPackages(signal?: AbortSignal): Promise<CatalogPackage[]> {
  return apiRequest(root, { signal });
}
export function getPackage(
  kind: CatalogPackage["kind"],
  id: string,
  version: string,
  signal?: AbortSignal,
): Promise<CatalogPackage> {
  return apiRequest(packagePath({ kind, id, version }), { signal });
}
export function installPackage(file: File): Promise<CatalogPackage> {
  const body = new FormData();
  body.append("file", file);
  return apiRequest(root, { method: "POST", body });
}
export function uninstallPackage(item: CatalogPackage): Promise<void> {
  return apiRequest(packagePath(item), { method: "DELETE" });
}
export function applyTemplate(
  item: CatalogPackage,
  payload: TemplateApply,
): Promise<Screen> {
  return apiRequest(`${packagePath(item)}/apply`, {
    method: "POST",
    json: payload,
  });
}
export function importAdminPlugin(
  item: PluginPackage,
  signal?: AbortSignal,
): Promise<unknown> {
  return fetch(
    `${packagePath(item)}/files/${item.manifest.entry.split("/").map(encodeURIComponent).join("/")}`,
    { credentials: "same-origin", signal },
  ).then(importPluginResponse);
}
