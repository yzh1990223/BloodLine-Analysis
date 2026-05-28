import { useEffect, useState } from "react";
import { fetchFieldLineage } from "../api";
import { FieldLineageResponse, FieldMapping } from "../types";

interface FieldLineagePanelProps {
  tableKey: string;
}

function groupByField(mappings: FieldMapping[], key: "field"): Record<string, FieldMapping[]> {
  return mappings.reduce((acc, mapping) => {
    const field = mapping[key];
    if (!field) return acc;
    if (!acc[field]) {
      acc[field] = [];
    }
    acc[field].push(mapping);
    return acc;
  }, {} as Record<string, FieldMapping[]>);
}

export function FieldLineagePanel({ tableKey }: FieldLineagePanelProps) {
  const [data, setData] = useState<FieldLineageResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    async function load() {
      try {
        const response = await fetchFieldLineage(tableKey);
        if (active) {
          setData(response);
          setError(null);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "加载字段血缘失败");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, [tableKey]);

  if (loading) {
    return <p className="text-secondary">字段血缘加载中...</p>;
  }

  if (error) {
    return <p className="error">{error}</p>;
  }

  const upstreamGroups = groupByField(data?.upstream_fields ?? [], "field");
  const downstreamGroups = groupByField(data?.downstream_fields ?? [], "field");
  const allFields = Array.from(
    new Set([...Object.keys(upstreamGroups), ...Object.keys(downstreamGroups)])
  ).sort();

  if (allFields.length === 0) {
    return <p className="text-secondary">暂无字段级血缘数据</p>;
  }

  return (
    <div className="field-lineage-panel">
      {allFields.map((field) => (
        <div key={field} className="field-lineage-card">
          <h4 className="field-lineage-field-name">{field}</h4>

          {upstreamGroups[field] && upstreamGroups[field].length > 0 && (
            <div className="field-lineage-section">
              <span className="field-lineage-label">上游来源</span>
              <ul className="field-lineage-list">
                {upstreamGroups[field].map((item, index) => (
                  <li key={`up-${index}`} className="field-lineage-item">
                    <span className="field-lineage-table">
                      {item.source_table?.display_name ?? item.source_table?.name ?? "未知表"}
                    </span>
                    <span className="field-lineage-dot">.</span>
                    <span className="field-lineage-column">{item.source_field}</span>
                    {item.is_derived ? (
                      <span className="field-lineage-derived">（派生）</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {downstreamGroups[field] && downstreamGroups[field].length > 0 && (
            <div className="field-lineage-section">
              <span className="field-lineage-label">下游目标</span>
              <ul className="field-lineage-list">
                {downstreamGroups[field].map((item, index) => (
                  <li key={`down-${index}`} className="field-lineage-item">
                    <span className="field-lineage-table">
                      {item.target_table?.display_name ?? item.target_table?.name ?? "未知表"}
                    </span>
                    <span className="field-lineage-dot">.</span>
                    <span className="field-lineage-column">{item.target_field}</span>
                    {item.is_derived ? (
                      <span className="field-lineage-derived">（派生）</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
