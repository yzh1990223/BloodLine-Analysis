import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { searchTables } from "../api";
import { ObjectTypeBadge, objectTypeLabel } from "../components/ObjectTypeBadge";
import { SearchBar } from "../components/SearchBar";
import { TableSummary } from "../types";

function normalizedObjectType(objectType: string | undefined): string {
  return objectType ?? "data_table";
}

export function ObjectListPage() {
  const [searchParams] = useSearchParams();
  const [items, setItems] = useState<TableSummary[]>([]);
  const [filteredItems, setFilteredItems] = useState<TableSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const objectType = searchParams.get("type");
  const currentTypeLabel = objectType ? objectTypeLabel(objectType) : "全部对象";

  useEffect(() => {
    const signal = { cancelled: false };

    async function loadItems() {
      setLoading(true);
      setError(null);
      try {
        const response = await searchTables("");
        if (signal.cancelled) {
          return;
        }
        setItems(response.items);
      } catch (err) {
        if (signal.cancelled) {
          return;
        }
        setError(err instanceof Error ? err.message : "加载对象列表失败");
        setItems([]);
      } finally {
        if (!signal.cancelled) {
          setLoading(false);
        }
      }
    }

    void loadItems();

    return () => {
      signal.cancelled = true;
    };
  }, []);

  useEffect(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const nextItems = items.filter((item) => {
      const matchesType = objectType ? normalizedObjectType(item.object_type) === objectType : true;
      const matchesQuery = normalizedQuery ? item.name.toLowerCase().includes(normalizedQuery) : true;
      return matchesType && matchesQuery;
    });
    setFilteredItems(nextItems);
  }, [items, objectType, query]);

  return (
    <main className="page">
      <header className="page-header">
        <p className="eyebrow">BloodLine Analysis</p>
        <h1>按类型浏览对象</h1>
        <p className="subtitle">按对象类型查看当前扫描结果，并从列表快速进入详情页。</p>
      </header>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>筛选结果</h2>
            <p className="panel-subtitle">当前类型：{currentTypeLabel}</p>
          </div>
        </div>

        <SearchBar defaultValue={query} placeholder="搜索对象名称" ariaLabel="搜索对象名称" onSearch={setQuery} />

        {loading ? <p>对象列表加载中...</p> : null}
        {error ? <p className="error">{error}</p> : null}
        {!loading && !error ? (
          <ul className="result-list object-list">
            {filteredItems.length === 0 ? <li>暂无匹配对象。</li> : null}
            {filteredItems.map((item) => (
              <li key={item.key} className="object-list-item">
                <div className="object-list-main">
                  <Link to={`/tables/${encodeURIComponent(item.key)}`}>{item.display_name ?? item.name}</Link>
                  <ObjectTypeBadge objectType={item.object_type} />
                </div>
                <span className="object-list-key">{item.key}</span>
              </li>
            ))}
          </ul>
        ) : null}
      </section>
    </main>
  );
}
