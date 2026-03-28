import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { fetchTableLineage, searchTables } from "../api";
import { ConnectedLineageGraph } from "../components/ConnectedLineageGraph";
import { LineageGraph } from "../components/LineageGraph";
import { ObjectTypeBadge } from "../components/ObjectTypeBadge";
import { RelatedObjectsPanel } from "../components/RelatedObjectsPanel";
import { TableLineageResponse } from "../types";

function collectConnectedLineages(
  currentTableKey: string,
  lineages: TableLineageResponse[],
): TableLineageResponse[] {
  const neighbors = new Map<string, Set<string>>();

  function ensureNode(key: string) {
    if (!neighbors.has(key)) {
      neighbors.set(key, new Set<string>());
    }
    return neighbors.get(key)!;
  }

  for (const lineage of lineages) {
    const tableKey = lineage.table?.key;
    if (!tableKey) {
      continue;
    }
    ensureNode(tableKey);

    for (const upstream of lineage.upstream_tables) {
      ensureNode(tableKey).add(upstream.key);
      ensureNode(upstream.key).add(tableKey);
    }

    for (const downstream of lineage.downstream_tables) {
      ensureNode(tableKey).add(downstream.key);
      ensureNode(downstream.key).add(tableKey);
    }
  }

  const visited = new Set<string>();
  const queue = [currentTableKey];

  while (queue.length > 0) {
    const key = queue.shift();
    if (!key || visited.has(key)) {
      continue;
    }
    visited.add(key);
    for (const next of neighbors.get(key) ?? []) {
      if (!visited.has(next)) {
        queue.push(next);
      }
    }
  }

  return lineages.filter((lineage) => lineage.table && visited.has(lineage.table.key));
}

export function TableDetailPage() {
  // Detail views are keyed by the stable backend table key.
  const navigate = useNavigate();
  const { tableKey = "" } = useParams();
  const decodedTableKey = decodeURIComponent(tableKey);
  const [lineage, setLineage] = useState<TableLineageResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [chainLineages, setChainLineages] = useState<TableLineageResponse[]>([]);
  const [chainLoading, setChainLoading] = useState(true);
  const [chainError, setChainError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const [response, catalog] = await Promise.all([
          fetchTableLineage(decodedTableKey),
          searchTables(""),
        ]);
        const allLineages = await Promise.all(
          catalog.items.map((item) => fetchTableLineage(item.key)),
        );
        if (active) {
          setLineage(response);
          setError(null);
          setChainLineages(collectConnectedLineages(decodedTableKey, allLineages));
          setChainError(null);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "加载血缘信息失败");
        }
      } finally {
        if (active) {
          setChainLoading(false);
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
        <p className="eyebrow">对象详情</p>
        <h1>{tableName}</h1>
        {lineage?.table ? <ObjectTypeBadge objectType={lineage.table.object_type} /> : null}
        <div className="page-actions">
          <Link to="/">返回总览</Link>
          <Link to={`/tables/${encodeURIComponent(decodedTableKey)}/impact`}>
            查看影响分析
          </Link>
        </div>
      </header>

      {chainError ? <p className="error">{chainError}</p> : null}
      {!chainError && chainLoading ? <p>完整链路图加载中...</p> : null}
      {!chainError && !chainLoading && chainLineages.length > 0 ? (
        <ConnectedLineageGraph
          currentTableKey={decodedTableKey}
          lineages={chainLineages}
          onTableSelect={(tableKey) => navigate(`/tables/${encodeURIComponent(tableKey)}`)}
        />
      ) : null}

      <LineageGraph
        tableName={tableName}
        objectType={lineage?.table?.object_type}
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
