// Shared frontend response models mirroring the backend JSON contract.
export interface TableSummary {
  id: number;
  key: string;
  name: string;
}

export interface RelatedObjectSummary {
  id: number;
  key: string;
  name: string;
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
