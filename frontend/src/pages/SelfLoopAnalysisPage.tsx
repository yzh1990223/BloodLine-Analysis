import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchCycleGroups } from "../api";
import { ObjectTypeBadge } from "../components/ObjectTypeBadge";
import { CycleGroupSummaryResponse } from "../types";

export function SelfLoopAnalysisPage() {
  const [payload, setPayload] = useState<CycleGroupSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const signal = { cancelled: false };

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const response = await fetchCycleGroups();
        if (!signal.cancelled) {
          setPayload(response);
        }
      } catch (err) {
        if (!signal.cancelled) {
          setError(err instanceof Error ? err.message : "加载闭环分析失败");
          setPayload(null);
        }
      } finally {
        if (!signal.cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      signal.cancelled = true;
    };
  }, []);

  return (
    <main className="page">
      <header className="page-header">
        <p className="eyebrow">BloodLine Analysis</p>
        <h1>闭环分析</h1>
        <p className="subtitle">按闭环组查看当前血缘图中彼此可达的表，快速定位异常循环链路。</p>
      </header>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>闭环概览</h2>
            <p className="panel-subtitle">每个闭环组对应一个至少包含 2 张表的强连通分量。</p>
          </div>
        </div>

        {loading ? <p>闭环分析加载中...</p> : null}
        {error ? <p className="error">{error}</p> : null}
        {!loading && !error && payload ? (
          <div className="overview-stats">
            <div className="overview-stat-card">
              <span>闭环组数量</span>
              <strong>{payload.summary.group_count}</strong>
            </div>
            <div className="overview-stat-card">
              <span>闭环表总数</span>
              <strong>{payload.summary.table_count}</strong>
            </div>
            <div className="overview-stat-card">
              <span>组内闭环边总数</span>
              <strong>{payload.summary.edge_count}</strong>
            </div>
          </div>
        ) : null}
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>闭环组列表</h2>
            <p className="panel-subtitle">每组展示参与闭环的表集合，点击对象名可进入详情页。</p>
          </div>
        </div>

        {!loading && !error && payload ? (
          <div className="cycle-group-list">
            {payload.items.length === 0 ? <p>当前没有发现多表闭环组。</p> : null}
            {payload.items.map((item, index) => (
              <section key={item.group_key} className="cycle-group-card">
                <div className="panel-header">
                  <div>
                    <h3>{`闭环组 ${index + 1}`}</h3>
                    <p className="panel-subtitle">{`${item.table_count} 张表 · ${item.edge_count} 条组内边`}</p>
                  </div>
                </div>
                <ul className="result-list object-list">
                  {item.tables.map((table) => (
                    <li key={table.key} className="object-list-item">
                      <div className="object-list-main object-loop-main">
                        <Link
                          to={`/tables/${encodeURIComponent(table.key)}`}
                          aria-label={`查看 ${table.name} 详情`}
                        >
                          {table.name}
                        </Link>
                        <ObjectTypeBadge objectType={table.object_type} />
                      </div>
                      <span className="object-list-key">{table.key}</span>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        ) : null}
      </section>
    </main>
  );
}
