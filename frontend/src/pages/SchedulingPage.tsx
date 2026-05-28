import { useEffect, useState } from "react";
import { fetchSchedulingLineage } from "../api";
import { SchedulingLineageItem, SchedulingLineageResponse } from "../types";

const ACTOR_TYPE_LABELS: Record<string, string> = {
  kettle: "Kettle",
  java: "Java",
  finereport: "FineReport",
  api: "API",
  finereport_file: "FineReport文件",
};

function actorTypeLabel(type: string): string {
  return ACTOR_TYPE_LABELS[type] ?? type;
}

export function SchedulingPage() {
  const [sourceQuery, setSourceQuery] = useState("");
  const [targetQuery, setTargetQuery] = useState("");
  const [items, setItems] = useState<SchedulingLineageItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load(source?: string, target?: string) {
    setLoading(true);
    setError(null);
    try {
      const response: SchedulingLineageResponse = await fetchSchedulingLineage(
        source,
        target,
      );
      setItems(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载调度血缘失败");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function handleSearch() {
    load(sourceQuery || undefined, targetQuery || undefined);
  }

  return (
    <div className="page-container">
      <h1>调度查看</h1>
      <p className="subtitle">以报表形式查看血缘来源、目标及其对应的解析来源。</p>

      <div className="panel">
        <div className="scheduling-filters">
          <label>
            血缘来源
            <input
              type="text"
              placeholder="输入血缘来源模糊搜索"
              value={sourceQuery}
              onChange={(e) => setSourceQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSearch();
              }}
            />
          </label>
          <label>
            血缘目标
            <input
              type="text"
              placeholder="输入血缘目标模糊搜索"
              value={targetQuery}
              onChange={(e) => setTargetQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSearch();
              }}
            />
          </label>
          <button type="button" className="primary-action" onClick={handleSearch}>
            查询
          </button>
        </div>
      </div>

      {loading ? <p>加载中...</p> : null}
      {error ? <p className="error">{error}</p> : null}

      {!loading && !error ? (
        <div className="panel">
          <div className="panel-header">
            <h2>血缘调度报表</h2>
            <p className="panel-subtitle">共 {items.length} 条记录</p>
          </div>
          {items.length === 0 ? (
            <p>暂无匹配的血缘记录</p>
          ) : (
            <table className="scheduling-table">
              <thead>
                <tr>
                  <th>血缘来源</th>
                  <th>血缘目标</th>
                  <th>来源类型</th>
                  <th>具体名称</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, index) => (
                  <tr key={`${item.source_name}-${item.target_name}-${item.actor_name}-${index}`}>
                    <td>{item.source_name}</td>
                    <td>{item.target_name}</td>
                    <td>{actorTypeLabel(item.actor_type)}</td>
                    <td>{item.actor_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      ) : null}
    </div>
  );
}
