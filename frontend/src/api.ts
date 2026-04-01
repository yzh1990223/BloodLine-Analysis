import {
  ConnectedLineageResponse,
  CreateScanResponse,
  CycleGroupSummaryResponse,
  LatestScanRunResponse,
  ScanRequestPayload,
  ScanFailureSummaryResponse,
  SearchResponse,
  TableImpactResponse,
  TableLineageResponse,
} from "./types";

// The frontend talks to the colocated backend by default, but can be pointed elsewhere.
const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  // Centralize fetch error handling so pages only deal with domain data.
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const errorBody = (await response.json()) as { detail?: string };
      if (errorBody?.detail) {
        message = errorBody.detail;
      }
    } catch {
      // Fall back to the generic status-based message when no JSON body is available.
    }
    throw new Error(message);
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

export function fetchConnectedLineage(tableKey: string): Promise<ConnectedLineageResponse> {
  /** Load the detail-page directional lineage subgraph in one request. */
  return requestJson<ConnectedLineageResponse>(
    `/api/tables/${encodeURIComponent(tableKey)}/connected-lineage`,
  );
}

export function fetchTableImpact(tableKey: string): Promise<TableImpactResponse> {
  /** Load downstream impact expansion for one table. */
  return requestJson<TableImpactResponse>(
    `/api/tables/${encodeURIComponent(tableKey)}/impact`,
  );
}

export function fetchLatestScanRun(): Promise<LatestScanRunResponse> {
  /** Load the most recent scan run for the scan control panel. */
  return requestJson<LatestScanRunResponse>("/api/scan-runs/latest");
}

export function createScan(payload: ScanRequestPayload): Promise<CreateScanResponse> {
  /** Trigger a new scan using the provided manual inputs. */
  return requestJson<CreateScanResponse>("/api/scan", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function fetchCycleGroups(): Promise<CycleGroupSummaryResponse> {
  /** Load grouped multi-table closed loops for the dedicated analysis page. */
  return requestJson<CycleGroupSummaryResponse>("/api/analysis/cycles");
}

export function fetchLatestScanFailures(): Promise<ScanFailureSummaryResponse> {
  /** Load the latest scan failure summary grouped by source and file. */
  return requestJson<ScanFailureSummaryResponse>("/api/scan-runs/latest/failures");
}
