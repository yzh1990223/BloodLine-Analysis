import { TableSummary } from "../types";

interface LineageGraphProps {
  tableName: string;
  upstreamTables: TableSummary[];
  downstreamTables: TableSummary[];
}

export function LineageGraph({
  tableName,
  upstreamTables,
  downstreamTables,
}: LineageGraphProps) {
  // The MVP uses a textual three-column layout instead of a full graph canvas.
  return (
    <section className="panel">
      <h2>血缘关系</h2>
      <div className="lineage-grid">
        <div>
          <h3>上游</h3>
          <ul>
            {upstreamTables.length === 0 ? <li>无</li> : null}
            {upstreamTables.map((table) => (
              <li key={table.key}>{table.name}</li>
            ))}
          </ul>
        </div>
        <div className="lineage-focus">
          <span>{tableName}</span>
        </div>
        <div>
          <h3>下游</h3>
          <ul>
            {downstreamTables.length === 0 ? <li>无</li> : null}
            {downstreamTables.map((table) => (
              <li key={table.key}>{table.name}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
