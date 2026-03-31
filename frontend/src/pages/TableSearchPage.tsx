import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { fetchCycleGroups, fetchTableLineage, searchTables } from "../api";
import { ObjectTypeBadge } from "../components/ObjectTypeBadge";
import { OverviewGraph } from "../components/OverviewGraph";
import { ScanControlPanel } from "../components/ScanControlPanel";
import { SearchBar } from "../components/SearchBar";
import { CycleGroupSummaryResponse, TableLineageResponse, TableSummary } from "../types";

interface OverviewStatCardProps {
  label: string;
  value: number;
  to: string;
  linkLabel: string;
}

function OverviewStatCard({ label, value, to, linkLabel }: OverviewStatCardProps) {
  return (
    <Link className="overview-stat-card overview-stat-link" to={to} aria-label={linkLabel}>
      <span>{label}</span>
      <strong>{value}</strong>
    </Link>
  );
}

export function TableSearchPage() {
  // The landing page emphasizes search and local previews so large scans stay responsive.
  const navigate = useNavigate();
  const [catalogItems, setCatalogItems] = useState<TableSummary[]>([]);
  const [items, setItems] = useState<TableSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedItem, setSelectedItem] = useState<TableSummary | null>(null);
  const [previewLineage, setPreviewLineage] = useState<TableLineageResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [cycleSummary, setCycleSummary] = useState<CycleGroupSummaryResponse["summary"]>({
    group_count: 0,
    table_count: 0,
    edge_count: 0,
  });

  async function loadCatalog(signal?: { cancelled: boolean }) {
    setCatalogLoading(true);
    setCatalogError(null);
    try {
      const [catalogResponse, cycleResponse] = await Promise.all([
        searchTables(""),
        fetchCycleGroups().catch(() => ({
          summary: { group_count: 0, table_count: 0, edge_count: 0 },
          items: [],
        })),
      ]);
      if (signal?.cancelled) {
        return;
      }
      setCatalogItems(catalogResponse.items);
      setCycleSummary(cycleResponse.summary);
    } catch (err) {
      if (signal?.cancelled) {
        return;
      }
      setCatalogError(err instanceof Error ? err.message : "加载对象概览失败");
    } finally {
      if (!signal?.cancelled) {
        setCatalogLoading(false);
      }
    }
  }

  useEffect(() => {
    const signal = { cancelled: false };
    void loadCatalog(signal);
    return () => {
      signal.cancelled = true;
    };
  }, []);

  async function loadPreview(item: TableSummary) {
    setSelectedItem(item);
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const response = await fetchTableLineage(item.key);
      setPreviewLineage(response);
    } catch (err) {
      setPreviewLineage(null);
      setPreviewError(err instanceof Error ? err.message : "加载局部血缘失败");
    } finally {
      setPreviewLoading(false);
    }
  }

  async function handleSearch(query: string) {
    setLoading(true);
    setError(null);
    try {
      const response = await searchTables(query);
      setItems(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "搜索失败");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page">
      <header className="page-header">
        <p className="eyebrow">BloodLine Analysis</p>
        <h1>表搜索</h1>
        <p className="subtitle">搜索源表、源文件和数据表，并查看跨 Kettle 与 Java 的数据血缘。</p>
      </header>

      <ScanControlPanel onScanCompleted={() => loadCatalog()} />

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>对象概览</h2>
            <p className="panel-subtitle">首页默认只展示统计与搜索，避免大图拖慢页面。</p>
          </div>
        </div>
        {catalogLoading ? <p>对象概览加载中...</p> : null}
        {catalogError ? <p className="error">{catalogError}</p> : null}
        {!catalogLoading && !catalogError ? (
          <div className="overview-stats">
            <OverviewStatCard
              label="总对象数"
              value={catalogItems.length}
              to="/objects"
              linkLabel="查看全部对象列表"
            />
            <OverviewStatCard
              label="源表"
              value={catalogItems.filter((item) => item.object_type === "source_table").length}
              to="/objects?type=source_table"
              linkLabel="查看源表对象列表"
            />
            <OverviewStatCard
              label="源文件"
              value={catalogItems.filter((item) => item.object_type === "source_file").length}
              to="/objects?type=source_file"
              linkLabel="查看源文件对象列表"
            />
            <OverviewStatCard
              label="数据表"
              value={catalogItems.filter((item) => (item.object_type ?? "data_table") === "data_table").length}
              to="/objects?type=data_table"
              linkLabel="查看数据表对象列表"
            />
            <OverviewStatCard
              label="API接口"
              value={catalogItems.filter((item) => item.object_type === "api_endpoint").length}
              to="/objects?type=api_endpoint"
              linkLabel="查看 API 接口对象列表"
            />
            <OverviewStatCard
              label="闭环分析"
              value={cycleSummary.group_count}
              to="/analysis/cycles"
              linkLabel="查看闭环分析页面"
            />
          </div>
        ) : null}
      </section>

      <div id="table-search">
        <SearchBar onSearch={handleSearch} />
      </div>

      {loading ? <p>加载中...</p> : null}
      {error ? <p className="error">{error}</p> : null}

      <section className="panel">
        <h2>搜索结果</h2>
        <ul className="result-list">
          {items.length === 0 ? <li>暂无结果。</li> : null}
          {items.map((item) => (
            <li key={item.key}>
              <Link to={`/tables/${encodeURIComponent(item.key)}`}>{item.name}</Link>
              <ObjectTypeBadge objectType={item.object_type} />
              <button
                type="button"
                className="link-button"
                onClick={() => void loadPreview(item)}
              >
                预览 {item.name}
              </button>
            </li>
          ))}
        </ul>
      </section>

      {previewLoading ? <p>局部血缘加载中...</p> : null}
      {previewError ? <p className="error">{previewError}</p> : null}
      {selectedItem && previewLineage && !previewLoading ? (
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>局部血缘预览</h2>
              <p className="panel-subtitle">
                当前仅渲染所选对象的直接上下游，双击节点可进入详情页。
              </p>
            </div>
          </div>
          <OverviewGraph
            lineages={[previewLineage]}
            onTableSelect={(tableKey) => navigate(`/tables/${encodeURIComponent(tableKey)}`)}
          />
        </section>
      ) : null}
    </main>
  );
}
