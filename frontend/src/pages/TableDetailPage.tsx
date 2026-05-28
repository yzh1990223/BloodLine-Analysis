import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { fetchConnectedLineage } from "../api";
import { ConnectedLineageGraph } from "../components/ConnectedLineageGraph";
import { FieldLineagePanel } from "../components/FieldLineagePanel";
import { ObjectTypeBadge } from "../components/ObjectTypeBadge";
import { RelatedObjectsPanel } from "../components/RelatedObjectsPanel";
import { ConnectedLineageResponse, TableLineageResponse } from "../types";

type DetailTab = "graph" | "fields" | "metadata";

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
  const [activeTab, setActiveTab] = useState<DetailTab>("graph");

  useEffect(() => {
    let active = true;
    setChainLoading(true);
    setChainError(null);
    setActiveRelatedObjectKey(null);
    setHighlightedTableKeys([]);
    setActiveTab("graph");

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

  const tableName = lineage?.table?.display_name ?? lineage?.table?.name ?? decodedTableKey;
  const technicalTableName = lineage?.table?.name ?? decodedTableKey;
  const diagnostics = lineage?.table?.payload?.diagnostics;
  const metadata = lineage?.table?.metadata;

  return (
    <main className="page">
      <header className="page-header">
        <p className="eyebrow">对象详情</p>
        <h1>{tableName}</h1>
        {technicalTableName !== tableName ? <p className="subtitle">{technicalTableName}</p> : null}
        {lineage?.table ? <ObjectTypeBadge objectType={lineage.table.object_type} /> : null}
        <div className="page-actions">
          <Link to="/">返回总览</Link>
          <Link to={`/tables/${encodeURIComponent(decodedTableKey)}/impact`}>
            查看影响分析
          </Link>
        </div>
      </header>

      <div className="detail-tabs">
        <button
          type="button"
          className={`detail-tab ${activeTab === "graph" ? "active" : ""}`}
          onClick={() => setActiveTab("graph")}
        >
          血缘图
        </button>
        <button
          type="button"
          className={`detail-tab ${activeTab === "fields" ? "active" : ""}`}
          onClick={() => setActiveTab("fields")}
        >
          字段血缘
        </button>
        <button
          type="button"
          className={`detail-tab ${activeTab === "metadata" ? "active" : ""}`}
          onClick={() => setActiveTab("metadata")}
        >
          元数据
        </button>
      </div>

      {activeTab === "graph" && (
        <>
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
                api_endpoints: [],
                transformations: [],
              }
            }
          />
        </>
      )}

      {activeTab === "fields" && (
        <section className="panel">
          <h2>字段血缘</h2>
          <FieldLineagePanel tableKey={decodedTableKey} />
        </section>
      )}

      {activeTab === "metadata" && (
        <>
          {metadata ? (
            <section className="panel">
              <h2>元数据摘要</h2>
              <div className="metadata-summary">
                <div className="metadata-row">
                  <span className="metadata-label">数据库</span>
                  <span className="metadata-value">{metadata.database_name}</span>
                </div>
                <div className="metadata-row">
                  <span className="metadata-label">技术名称</span>
                  <span className="metadata-value">{metadata.object_name}</span>
                </div>
                <div className="metadata-row">
                  <span className="metadata-label">对象种类</span>
                  <span className="metadata-value">{metadata.object_kind}</span>
                </div>
                <div className="metadata-row">
                  <span className="metadata-label">字段数</span>
                  <span className="metadata-value">{metadata.column_count}</span>
                </div>
                {metadata.comment ? (
                  <div className="metadata-row">
                    <span className="metadata-label">中文名称</span>
                    <span className="metadata-value">{metadata.comment}</span>
                  </div>
                ) : null}
                {metadata.object_kind === "view" && metadata.view_definition ? (
                  <>
                    <div className="metadata-row">
                      <span className="metadata-label">视图定义</span>
                    </div>
                    <pre className="metadata-sql">{metadata.view_definition}</pre>
                  </>
                ) : null}
                {metadata.object_kind === "view" && metadata.view_parse_status === "failed" ? (
                  <>
                    <div className="metadata-row">
                      <span className="metadata-label">视图解析状态</span>
                      <span className="metadata-value error-text">失败</span>
                    </div>
                    {metadata.view_parse_error ? (
                      <div className="metadata-row">
                        <span className="metadata-label">失败原因</span>
                        <span className="metadata-value error-text">{metadata.view_parse_error}</span>
                      </div>
                    ) : null}
                  </>
                ) : null}
              </div>
            </section>
          ) : null}

          {lineage?.table?.object_type === "api_endpoint" && diagnostics ? (
            <section className="panel">
              <h2>API 诊断</h2>
              <div className="api-diagnostics-list">
                <div className="metadata-row">
                  <span className="metadata-label">已解析调用</span>
                  <span className="metadata-value">{diagnostics.resolved_calls}</span>
                </div>
                <div className="metadata-row">
                  <span className="metadata-label">未解析调用</span>
                  <span className="metadata-value">{diagnostics.unresolved_calls}</span>
                </div>
                <div className="metadata-row">
                  <span className="metadata-label">读表数</span>
                  <span className="metadata-value">{diagnostics.read_table_count}</span>
                </div>
                <div className="metadata-row">
                  <span className="metadata-label">写表数</span>
                  <span className="metadata-value">{diagnostics.write_table_count}</span>
                </div>
                {diagnostics.unresolved_reasons.length > 0 ? (
                  <>
                    <div className="metadata-row">
                      <span className="metadata-label">未解析原因</span>
                    </div>
                    <ul className="diagnostic-item-list">
                      {diagnostics.unresolved_reasons.map((item) => (
                        <li key={`${item.call}:${item.reason}`} className="diagnostic-item">
                          <p className="diagnostic-item-call">{item.call}</p>
                          <p className="diagnostic-item-reason">{item.reason}</p>
                        </li>
                      ))}
                    </ul>
                  </>
                ) : (
                  <p>未解析原因：暂无</p>
                )}
              </div>
            </section>
          ) : null}
        </>
      )}
    </main>
  );
}
