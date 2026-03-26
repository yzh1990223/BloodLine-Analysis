import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchTableLineage } from "../api";
import { LineageGraph } from "../components/LineageGraph";
import { RelatedObjectsPanel } from "../components/RelatedObjectsPanel";
import { TableLineageResponse } from "../types";

export function TableDetailPage() {
  const { tableKey = "" } = useParams();
  const decodedTableKey = decodeURIComponent(tableKey);
  const [lineage, setLineage] = useState<TableLineageResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const response = await fetchTableLineage(decodedTableKey);
        if (active) {
          setLineage(response);
          setError(null);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load lineage");
        }
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, [decodedTableKey]);

  if (error) {
    return <main className="page"><p className="error">{error}</p></main>;
  }

  const tableName = lineage?.table?.name ?? decodedTableKey;

  return (
    <main className="page">
      <header className="page-header">
        <p className="eyebrow">Table Detail</p>
        <h1>{tableName}</h1>
        <Link to={`/tables/${encodeURIComponent(decodedTableKey)}/impact`}>
          View impact analysis
        </Link>
      </header>

      <LineageGraph
        tableName={tableName}
        upstreamTables={lineage?.upstream_tables ?? []}
        downstreamTables={lineage?.downstream_tables ?? []}
      />

      <RelatedObjectsPanel
        relatedObjects={
          lineage?.related_objects ?? {
            jobs: [],
            java_modules: [],
            transformations: [],
          }
        }
      />
    </main>
  );
}
