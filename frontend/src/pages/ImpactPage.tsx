import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchTableImpact } from "../api";
import { TableImpactResponse } from "../types";

export function ImpactPage() {
  // Impact uses the backend's multi-hop traversal rather than recomputing on the client.
  const { tableKey = "" } = useParams();
  const decodedTableKey = decodeURIComponent(tableKey);
  const [impact, setImpact] = useState<TableImpactResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const response = await fetchTableImpact(decodedTableKey);
        if (active) {
          setImpact(response);
          setError(null);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "加载影响分析失败");
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

  return (
    <main className="page">
      <header className="page-header">
        <p className="eyebrow">影响分析</p>
        <h1>{impact?.table?.name ?? decodedTableKey}</h1>
        <Link to={`/tables/${encodeURIComponent(decodedTableKey)}`}>返回表详情</Link>
      </header>

      <section className="panel">
        <h2>受影响的表</h2>
        <ul className="result-list">
          {impact?.impacted_tables.length ? null : <li>未发现下游影响。</li>}
          {impact?.impacted_tables.map((table) => (
            <li key={`${table.key}-${table.hop}`}>
              <span>{table.name}</span>
              <small>第 {table.hop} 跳</small>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
