// Shared frontend response models mirroring the backend JSON contract.
export interface TableSummary {
  id: number;
  key: string;
  name: string;
  display_name?: string;
  object_type?: string;
  metadata?: ObjectMetadataSummary;
}

export interface ObjectMetadataSummary {
  database_name: string;
  object_name: string;
  object_kind: string;
  comment: string | null;
  column_count: number;
  view_definition?: string | null;
  view_parse_status?: string;
  view_parse_error?: string | null;
  metadata_source: string;
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
  api_endpoints: RelatedObjectSummary[];
  transformations: RelatedObjectSummary[];
}

export interface TableLineageResponse {
  table: TableSummary | null;
  upstream_tables: TableSummary[];
  downstream_tables: TableSummary[];
  related_objects: RelatedObjects;
}

export interface ConnectedLineageResponse {
  table_lineage: TableLineageResponse | null;
  items: TableLineageResponse[];
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

export interface SelfLoopSummaryItem extends TableSummary {
  self_loop_count: number;
}

export interface SelfLoopSummaryResponse {
  summary: {
    table_count: number;
    self_loop_count: number;
  };
  items: SelfLoopSummaryItem[];
}

export interface CycleGroupSummaryItem {
  group_key: string;
  table_count: number;
  edge_count: number;
  tables: Array<TableSummary & { cycle_edge_count: number }>;
}

export interface CycleGroupSummaryResponse {
  summary: {
    group_count: number;
    table_count: number;
    edge_count: number;
  };
  items: CycleGroupSummaryItem[];
}

export interface ScanFailureRecord {
  id: number;
  scan_run_id: number;
  source_type: string;
  file_path: string;
  failure_type: string;
  message: string;
  object_key?: string | null;
  sql_snippet?: string | null;
  created_at: string | null;
}

export interface ScanFailureFileGroup {
  file_path: string;
  failures: ScanFailureRecord[];
}

export interface ScanFailureSourceGroup {
  source_type: string;
  files: ScanFailureFileGroup[];
}

export interface ScanFailureSummaryResponse {
  scan_run: ScanRunSummary | null;
  summary: {
    scan_run_id: number | null;
    failure_count: number;
    file_count: number;
    source_counts: Record<string, number>;
  };
  groups: ScanFailureSourceGroup[];
}

export interface ScanRunSummary {
  id: number;
  status: string;
  inputs?: ScanRequestPayload;
  started_at: string | null;
  finished_at: string | null;
  created_at: string | null;
}

export interface LatestScanRunResponse {
  scan_run: ScanRunSummary | null;
}

export interface ScanRequestPayload {
  repo_path?: string;
  repo_paths?: string[];
  java_source_root?: string;
  java_source_roots?: string[];
  mysql_dsn?: string;
  metadata_databases?: string[];
}

export interface CreateScanResponse {
  scan_run_id: number;
  status: string;
  inputs: ScanRequestPayload;
}
