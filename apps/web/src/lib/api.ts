export interface HealthResponse {
  status: string;
  version: string;
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch("/api/health");
  if (!response.ok) {
    throw new Error(`Health request failed: ${response.status}`);
  }
  return response.json() as Promise<HealthResponse>;
}
