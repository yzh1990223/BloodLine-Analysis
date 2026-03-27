import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { fetchTableLineage, searchTables } from "../api";
import { OverviewGraph } from "../components/OverviewGraph";
import { SearchBar } from "../components/SearchBar";
import { TableLineageResponse, TableSummary } from "../types";

export function TableSearchPage() {
  // The landing page combines a full overview graph with focused table search.
  const navigate = useNavigate();
  const [items, setItems] = useState<TableSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [overviewLineages, setOverviewLineages] = useState<TableLineageResponse[]>([]);
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [overviewError, setOverviewError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadOverview() {
      setOverviewLoading(true);
      setOverviewError(null);
      try {
        const response = await searchTables("");
        const lineages = await Promise.all(
          response.items.map((item) => fetchTableLineage(item.key)),
        );
        if (!active) {
          return;
        }
        setOverviewLineages(lineages);
      } catch (err) {
        if (!active) {
          return;
        }
        setOverviewError(err instanceof Error ? err.message : "加载总览图失败");
      } finally {
        if (active) {
          setOverviewLoading(false);
        }
      }
    }

    void loadOverview();
    return () => {
      active = false;
    };
  }, []);

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
        <p className="subtitle">搜索 MySQL 表，并查看跨 Kettle 与 Java 的数据血缘。</p>
      </header>

      {overviewLoading ? <p>总览图加载中...</p> : null}
      {overviewError ? <p className="error">{overviewError}</p> : null}
      {!overviewLoading && !overviewError ? (
        <OverviewGraph
          lineages={overviewLineages}
          onTableSelect={(tableKey) => navigate(`/tables/${encodeURIComponent(tableKey)}`)}
        />
      ) : null}

      <SearchBar onSearch={handleSearch} />

      {loading ? <p>加载中...</p> : null}
      {error ? <p className="error">{error}</p> : null}

      <section className="panel">
        <h2>搜索结果</h2>
        <ul className="result-list">
          {items.length === 0 ? <li>暂无结果。</li> : null}
          {items.map((item) => (
            <li key={item.key}>
              <Link to={`/tables/${encodeURIComponent(item.key)}`}>{item.name}</Link>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
