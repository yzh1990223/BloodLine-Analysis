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
  return (
    <section className="panel">
      <h2>Lineage</h2>
      <div className="lineage-grid">
        <div>
          <h3>Upstream</h3>
          <ul>
            {upstreamTables.length === 0 ? <li>None</li> : null}
            {upstreamTables.map((table) => (
              <li key={table.key}>{table.name}</li>
            ))}
          </ul>
        </div>
        <div className="lineage-focus">
          <span>{tableName}</span>
        </div>
        <div>
          <h3>Downstream</h3>
          <ul>
            {downstreamTables.length === 0 ? <li>None</li> : null}
            {downstreamTables.map((table) => (
              <li key={table.key}>{table.name}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
