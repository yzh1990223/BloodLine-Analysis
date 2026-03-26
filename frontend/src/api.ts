import {
  SearchResponse,
  TableImpactResponse,
  TableLineageResponse,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export function searchTables(query: string): Promise<SearchResponse> {
  const params = new URLSearchParams();
  if (query) {
    params.set("q", query);
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return requestJson<SearchResponse>(`/api/tables/search${suffix}`);
}

export function fetchTableLineage(tableKey: string): Promise<TableLineageResponse> {
  return requestJson<TableLineageResponse>(
    `/api/tables/${encodeURIComponent(tableKey)}/lineage`,
  );
}

export function fetchTableImpact(tableKey: string): Promise<TableImpactResponse> {
  return requestJson<TableImpactResponse>(
    `/api/tables/${encodeURIComponent(tableKey)}/impact`,
  );
}
