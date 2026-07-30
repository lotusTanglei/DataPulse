import { apiRequest } from "../../lib/api";
import type { QueryRequest, QueryResult } from "./types";

export function runDatasourceQuery(
  datasourceId: string,
  payload: QueryRequest,
  signal?: AbortSignal,
): Promise<QueryResult> {
  return apiRequest<QueryResult>(
    `/api/admin/datasources/${encodeURIComponent(datasourceId)}/query`,
    {
      method: "POST",
      json: payload,
      signal,
    },
  );
}
