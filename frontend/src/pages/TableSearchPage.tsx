import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { fetchCycleGroups, fetchLatestScanRun, fetchTableLineage, searchTables } from "../api";
import { ObjectTypeBadge } from "../components/ObjectTypeBadge";
import { OverviewGraph } from "../components/OverviewGraph";
import { ScanControlPanel } from "../components/ScanControlPanel";
import { SearchBar } from "../components/SearchBar";
import { CycleGroupSummaryResponse, LatestScanRunResponse, TableLineageResponse, TableSummary } from "../types";

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
  const [syncing, setSyncing] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [latestScanRun, setLatestScanRun] = useState<LatestScanRunResponse["scan_run"]>(null);
  const [cycleSummary, setCycleSummary] = useState<CycleGroupSummaryResponse["summary"]>({
    group_count: 0,
    table_count: 0,
    edge_count: 0,
  });

  async function loadCatalog(signal?: { cancelled: boolean }) {
    setCatalogLoading(true);
    setCatalogError(null);
    try {
      const [catalogResponse, cycleResponse, latestResponse] = await Promise.all([
        searchTables(""),
        fetchCycleGroups().catch(() => ({
          summary: { group_count: 0, table_count: 0, edge_count: 0 },
          items: [],
        })),
        fetchLatestScanRun().catch(() => ({ scan_run: null })),
      ]);
      if (signal?.cancelled) {
        return;
      }
      setCatalogItems(catalogResponse.items);
      setCycleSummary(cycleResponse.summary);
      setLatestScanRun(latestResponse.scan_run);
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

  function formatErrorMessage(err: unknown): string {
    if (err instanceof Error) {
      return err.message;
    }
    if (typeof err === "string") {
      return err;
    }
    try {
      return JSON.stringify(err);
    } catch {
      return String(err);
    }
  }

  async function reportFailure(
    sourceType: string,
    filePath: string,
    failureType: string,
    err: unknown,
    objectKey?: string,
  ) {
    const message = formatErrorMessage(err);
    console.error(`${filePath} 失败:`, err);
    try {
      const { recordOperationFailure } = await import("../api");
      await recordOperationFailure({
        source_type: sourceType,
        file_path: filePath,
        failure_type: failureType,
        message,
        object_key: objectKey,
      });
    } catch (reportErr) {
      console.error("记录失败信息失败:", reportErr);
    }
    return message;
  }

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

      <div className="page-actions">
        <Link to="/scan-failures">查看最近扫描失败汇总</Link>
        <button
          type="button"
          className="export-button"
          disabled={exporting}
          onClick={async () => {
            setExporting(true);
            const dsn = latestScanRun?.inputs?.mysql_dsn;
            try {
              const url = dsn
                ? `/api/export/lineage/excel?mysql_dsn=${encodeURIComponent(dsn)}`
                : "/api/export/lineage/excel";
              const res = await fetch(url);
              if (!res.ok) {
                let detail = `HTTP ${res.status}`;
                try {
                  const body = (await res.json()) as { detail?: string };
                  if (body.detail) detail = body.detail;
                } catch {
                  // ignore
                }
                throw new Error(detail);
              }
              const blob = await res.blob();
              const downloadUrl = window.URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = downloadUrl;
              a.download = "lineage.xlsx";
              document.body.appendChild(a);
              a.click();
              a.remove();
              window.URL.revokeObjectURL(downloadUrl);
            } catch (err) {
              const message = await reportFailure("ui", "/api/export/lineage/excel", "export_error", err, dsn);
              alert(`导出失败: ${message}`);
            } finally {
              setExporting(false);
            }
          }}
        >
          {exporting ? "导出中..." : "导出血缘"}
        </button>
        <button
          type="button"
          className="sync-button"
          disabled={syncing}
          onClick={async () => {
            setSyncing(true);
            const dsn = latestScanRun?.inputs?.mysql_dsn;
            try {
              const { syncLineageToMySQL } = await import("../api");
              if (!dsn) {
                alert("未配置 MySQL DSN，请先在高级配置中填写");
                return;
              }
              const res = await syncLineageToMySQL(dsn);
              alert(res.message);
            } catch (err) {
              const message = await reportFailure("ui", "/api/sync/lineage/mysql", "sync_error", err, dsn);
              alert(`同步失败: ${message}`);
            } finally {
              setSyncing(false);
            }
          }}
        >
          {syncing ? "同步中..." : "血缘同步"}
        </button>
      </div>

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
              label="数据视图"
              value={catalogItems.filter((item) => item.object_type === "table_view").length}
              to="/objects?type=table_view"
              linkLabel="查看数据视图对象列表"
            />
            <OverviewStatCard
              label="API接口"
              value={catalogItems.filter((item) => item.object_type === "api_endpoint").length}
              to="/objects?type=api_endpoint"
              linkLabel="查看 API 接口对象列表"
            />
            <OverviewStatCard
              label="菜单"
              value={catalogItems.filter((item) => item.object_type === "menu").length}
              to="/objects?type=menu"
              linkLabel="查看菜单对象列表"
            />
            <OverviewStatCard
              label="帆软文件"
              value={catalogItems.filter((item) => item.object_type === "report_file").length}
              to="/objects?type=report_file"
              linkLabel="查看帆软文件对象列表"
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
