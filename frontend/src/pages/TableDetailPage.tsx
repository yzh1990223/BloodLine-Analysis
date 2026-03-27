import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchTableLineage } from "../api";
import { LineageGraph } from "../components/LineageGraph";
import { RelatedObjectsPanel } from "../components/RelatedObjectsPanel";
import { TableLineageResponse } from "../types";

export function TableDetailPage() {
  // Detail views are keyed by the stable backend table key.
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
          setError(err instanceof Error ? err.message : "加载血缘信息失败");
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
        <p className="eyebrow">表详情</p>
        <h1>{tableName}</h1>
        <Link to={`/tables/${encodeURIComponent(decodedTableKey)}/impact`}>
          查看影响分析
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
