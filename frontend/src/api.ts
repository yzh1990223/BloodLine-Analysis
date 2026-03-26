import {
  SearchResponse,
  TableImpactResponse,
  TableLineageResponse,
} from "./types";

// The frontend talks to the colocated backend by default, but can be pointed elsewhere.
const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function requestJson<T>(path: string): Promise<T> {
  // Centralize fetch error handling so pages only deal with domain data.
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export function searchTables(query: string): Promise<SearchResponse> {
  /** Search table summaries for the landing page. */
  const params = new URLSearchParams();
  if (query) {
    params.set("q", query);
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return requestJson<SearchResponse>(`/api/tables/search${suffix}`);
}

export function fetchTableLineage(tableKey: string): Promise<TableLineageResponse> {
  /** Load direct upstream/downstream lineage for one table. */
  return requestJson<TableLineageResponse>(
    `/api/tables/${encodeURIComponent(tableKey)}/lineage`,
  );
}

export function fetchTableImpact(tableKey: string): Promise<TableImpactResponse> {
  /** Load downstream impact expansion for one table. */
  return requestJson<TableImpactResponse>(
    `/api/tables/${encodeURIComponent(tableKey)}/impact`,
  );
}
