import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { fetchConnectedLineage } from "../api";
import { ConnectedLineageGraph } from "../components/ConnectedLineageGraph";
import { LineageGraph } from "../components/LineageGraph";
import { ObjectTypeBadge } from "../components/ObjectTypeBadge";
import { RelatedObjectsPanel } from "../components/RelatedObjectsPanel";
import { TableLineageResponse } from "../types";

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
  const [activeRelatedObjectKey, setActiveRelatedObjectKey] = useState<string | null>(null);
  const [highlightedTableKeys, setHighlightedTableKeys] = useState<string[]>([]);

  useEffect(() => {
    let active = true;
    setChainLoading(true);
    setChainError(null);
    setActiveRelatedObjectKey(null);
    setHighlightedTableKeys([]);

    async function load() {
      try {
        const response = await fetchConnectedLineage(decodedTableKey);
        if (active) {
          setLineage(response.table_lineage);
          setError(null);
          setChainLineages(response.items);
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

      {lineage?.table?.metadata ? (
        <section className="panel">
          <h2>元数据摘要</h2>
          <div className="metadata-summary">
            <p>数据库：{lineage.table.metadata.database_name}</p>
            <p>对象种类：{lineage.table.metadata.object_kind}</p>
            <p>字段数：{lineage.table.metadata.column_count}</p>
            {lineage.table.metadata.comment ? <p>注释：{lineage.table.metadata.comment}</p> : null}
          </div>
        </section>
      ) : null}

      {chainError ? <p className="error">{chainError}</p> : null}
      {!chainError && chainLoading ? <p>完整链路图加载中...</p> : null}
      {!chainError && !chainLoading && chainLineages.length > 0 ? (
        <ConnectedLineageGraph
          currentTableKey={decodedTableKey}
          lineages={chainLineages}
          highlightedTableKeys={highlightedTableKeys}
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
        activeObjectKey={activeRelatedObjectKey}
        onObjectSelect={(objectKey, relatedTableKeys) => {
          setActiveRelatedObjectKey(objectKey);
          setHighlightedTableKeys(objectKey ? relatedTableKeys : []);
        }}
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
