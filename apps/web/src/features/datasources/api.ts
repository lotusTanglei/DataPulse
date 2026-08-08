import { apiRequest } from "../../lib/api";
import type { QueryResult } from "../query/types";
import type {
  Datasource,
  DatasourceCreatePayload,
  DatasourceUpdatePayload,
  NamespaceInfo,
  RelationInfo,
  RelationSchema,
} from "./types";

const DATASOURCES_PATH = "/api/admin/datasources";

export function listDatasources(signal?: AbortSignal): Promise<Datasource[]> {
  return apiRequest<Datasource[]>(DATASOURCES_PATH, { signal });
}

export function getDatasource(
  datasourceId: string,
  signal?: AbortSignal,
): Promise<Datasource> {
  return apiRequest<Datasource>(
    `${DATASOURCES_PATH}/${encodeURIComponent(datasourceId)}`,
    { signal },
  );
}

export function createDatasource(
  payload: DatasourceCreatePayload,
): Promise<Datasource> {
  return apiRequest<Datasource>(DATASOURCES_PATH, {
    method: "POST",
    json: payload,
  });
}

export function updateDatasource(
  datasourceId: string,
  payload: DatasourceUpdatePayload,
): Promise<Datasource> {
  return apiRequest<Datasource>(
    `${DATASOURCES_PATH}/${encodeURIComponent(datasourceId)}`,
    {
      method: "PATCH",
      json: payload,
    },
  );
}

export function testDatasource(
  datasourceId: string,
  signal?: AbortSignal,
): Promise<Datasource> {
  return apiRequest<Datasource>(
    `${DATASOURCES_PATH}/${encodeURIComponent(datasourceId)}/test`,
    {
      method: "POST",
      signal,
    },
  );
}

export function listNamespaces(
  datasourceId: string,
  signal?: AbortSignal,
): Promise<NamespaceInfo[]> {
  return apiRequest<NamespaceInfo[]>(
    `${DATASOURCES_PATH}/${encodeURIComponent(datasourceId)}/namespaces`,
    { signal },
  );
}

export function listRelations(
  datasourceId: string,
  namespace: string | null,
  signal?: AbortSignal,
): Promise<RelationInfo[]> {
  const parameters = new URLSearchParams();
  parameters.set("namespace", namespace ?? "");
  return apiRequest<RelationInfo[]>(
    `${DATASOURCES_PATH}/${encodeURIComponent(datasourceId)}/relations?${parameters}`,
    { signal },
  );
}

export function describeRelation(
  datasourceId: string,
  namespace: string | null,
  relation: string,
  signal?: AbortSignal,
): Promise<RelationSchema> {
  const parameters = new URLSearchParams();
  parameters.set("namespace", namespace ?? "");
  parameters.set("relation", relation);
  return apiRequest<RelationSchema>(
    `${DATASOURCES_PATH}/${encodeURIComponent(datasourceId)}/relation?${parameters}`,
    { signal },
  );
}

export function previewRelation(
  datasourceId: string,
  namespace: string | null,
  relation: string,
  limit = 100,
  signal?: AbortSignal,
): Promise<QueryResult> {
  const parameters = new URLSearchParams();
  parameters.set("namespace", namespace ?? "");
  parameters.set("relation", relation);
  parameters.set("limit", String(limit));
  return apiRequest<QueryResult>(
    `${DATASOURCES_PATH}/${encodeURIComponent(datasourceId)}/relation/preview?${parameters}`,
    { signal },
  );
}
