import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { fetchTableLineage, searchTables } from "../api";
import { ConnectedLineageGraph } from "../components/ConnectedLineageGraph";
import { LineageGraph } from "../components/LineageGraph";
import { ObjectTypeBadge } from "../components/ObjectTypeBadge";
import { RelatedObjectsPanel } from "../components/RelatedObjectsPanel";
import { TableLineageResponse } from "../types";

function collectDirectionalLineages(
  currentTableKey: string,
  lineages: TableLineageResponse[],
): TableLineageResponse[] {
  const lineageByKey = new Map<string, TableLineageResponse>();
  const upstreamByNode = new Map<string, Set<string>>();
  const downstreamByNode = new Map<string, Set<string>>();

  function ensureDirectionMap(map: Map<string, Set<string>>, key: string) {
    if (!map.has(key)) {
      map.set(key, new Set<string>());
    }
    return map.get(key)!;
  }

  for (const lineage of lineages) {
    const tableKey = lineage.table?.key;
    if (!tableKey) {
      continue;
    }
    lineageByKey.set(tableKey, lineage);
    ensureDirectionMap(upstreamByNode, tableKey);
    ensureDirectionMap(downstreamByNode, tableKey);

    for (const upstream of lineage.upstream_tables) {
      ensureDirectionMap(upstreamByNode, tableKey).add(upstream.key);
      ensureDirectionMap(downstreamByNode, upstream.key).add(tableKey);
    }

    for (const downstream of lineage.downstream_tables) {
      ensureDirectionMap(downstreamByNode, tableKey).add(downstream.key);
      ensureDirectionMap(upstreamByNode, downstream.key).add(tableKey);
    }
  }

  function walkDirection(
    seed: string,
    adjacency: Map<string, Set<string>>,
    visited: Set<string>,
  ) {
    const queue = [seed];

    while (queue.length > 0) {
      const key = queue.shift();
      if (!key || visited.has(key)) {
        continue;
      }
      visited.add(key);
      for (const next of adjacency.get(key) ?? []) {
        if (!visited.has(next)) {
          queue.push(next);
        }
      }
    }
  }

  function collectDistanceMap(
    seed: string,
    adjacency: Map<string, Set<string>>,
  ): Map<string, number> {
    const distanceByNode = new Map<string, number>();
    const queue: Array<{ key: string; distance: number }> = [{ key: seed, distance: 0 }];

    while (queue.length > 0) {
      const current = queue.shift();
      if (!current || distanceByNode.has(current.key)) {
        continue;
      }
      distanceByNode.set(current.key, current.distance);
      for (const next of adjacency.get(current.key) ?? []) {
        if (!distanceByNode.has(next)) {
          queue.push({ key: next, distance: current.distance + 1 });
        }
      }
    }

    return distanceByNode;
  }

  const upstreamReachable = new Set<string>();
  const downstreamReachable = new Set<string>();
  walkDirection(currentTableKey, upstreamByNode, upstreamReachable);
  walkDirection(currentTableKey, downstreamByNode, downstreamReachable);
  const upstreamDistance = collectDistanceMap(currentTableKey, upstreamByNode);
  const downstreamDistance = collectDistanceMap(currentTableKey, downstreamByNode);

  const allowedKeys = new Set<string>([
    ...upstreamReachable,
    ...downstreamReachable,
    currentTableKey,
  ]);

  return Array.from(allowedKeys)
    .map((key) => lineageByKey.get(key))
    .filter((lineage): lineage is TableLineageResponse => Boolean(lineage))
    .map((lineage) => {
      const tableKey = lineage.table?.key;
      if (!tableKey) {
        return lineage;
      }

      return {
        ...lineage,
        upstream_tables: lineage.upstream_tables.filter((table) => {
          if (!allowedKeys.has(table.key)) {
            return false;
          }

          const sourceUpstreamDistance = upstreamDistance.get(table.key);
          const targetUpstreamDistance = upstreamDistance.get(tableKey);
          if (
            sourceUpstreamDistance !== undefined &&
            targetUpstreamDistance !== undefined &&
            sourceUpstreamDistance === targetUpstreamDistance + 1
          ) {
            return true;
          }

          const sourceDownstreamDistance = downstreamDistance.get(table.key);
          const targetDownstreamDistance = downstreamDistance.get(tableKey);
          if (
            sourceDownstreamDistance !== undefined &&
            targetDownstreamDistance !== undefined &&
            sourceDownstreamDistance + 1 === targetDownstreamDistance
          ) {
            return true;
          }

          return false;
        }),
        downstream_tables: lineage.downstream_tables.filter((table) => {
          if (!allowedKeys.has(table.key)) {
            return false;
          }

          const sourceUpstreamDistance = upstreamDistance.get(tableKey);
          const targetUpstreamDistance = upstreamDistance.get(table.key);
          if (
            sourceUpstreamDistance !== undefined &&
            targetUpstreamDistance !== undefined &&
            sourceUpstreamDistance === targetUpstreamDistance + 1
          ) {
            return true;
          }

          const sourceDownstreamDistance = downstreamDistance.get(tableKey);
          const targetDownstreamDistance = downstreamDistance.get(table.key);
          if (
            sourceDownstreamDistance !== undefined &&
            targetDownstreamDistance !== undefined &&
            sourceDownstreamDistance + 1 === targetDownstreamDistance
          ) {
            return true;
          }

          return false;
        }),
      };
    });
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
          setChainLineages(collectDirectionalLineages(decodedTableKey, allLineages));
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
