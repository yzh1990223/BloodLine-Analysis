// Shared frontend response models mirroring the backend JSON contract.
export interface TableSummary {
  id: number;
  key: string;
  name: string;
  object_type?: string;
}

export interface RelatedObjectSummary {
  id: number;
  key: string;
  name: string;
  related_table_keys?: string[];
}

export interface RelatedObjects {
  jobs: RelatedObjectSummary[];
  java_modules: RelatedObjectSummary[];
  transformations: RelatedObjectSummary[];
}

export interface TableLineageResponse {
  table: TableSummary | null;
  upstream_tables: TableSummary[];
  downstream_tables: TableSummary[];
  related_objects: RelatedObjects;
}

export interface ImpactedTable extends TableSummary {
  hop: number;
}

export interface TableImpactResponse extends TableLineageResponse {
  impacted_tables: ImpactedTable[];
}

export interface SearchResponse {
  items: TableSummary[];
}

export interface ScanRunSummary {
  id: number;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  created_at: string | null;
}

export interface LatestScanRunResponse {
  scan_run: ScanRunSummary | null;
}

export interface ScanRequestPayload {
  repo_path?: string;
  java_source_root?: string;
  mysql_dsn?: string;
}

export interface CreateScanResponse {
  scan_run_id: number;
  status: string;
  inputs: Record<string, string>;
}
