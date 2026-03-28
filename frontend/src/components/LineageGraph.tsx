import { ObjectTypeBadge } from "./ObjectTypeBadge";
import { TableSummary } from "../types";

interface LineageGraphProps {
  tableName: string;
  objectType?: string;
  upstreamTables: TableSummary[];
  downstreamTables: TableSummary[];
}

export function LineageGraph({
  tableName,
  objectType,
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
              <li key={table.key}>
                <span>{table.name}</span>
                <ObjectTypeBadge objectType={table.object_type} />
              </li>
            ))}
          </ul>
        </div>
        <div className="lineage-focus">
          <span>{tableName}</span>
          <ObjectTypeBadge objectType={objectType} />
        </div>
        <div>
          <h3>下游</h3>
          <ul>
            {downstreamTables.length === 0 ? <li>无</li> : null}
            {downstreamTables.map((table) => (
              <li key={table.key}>
                <span>{table.name}</span>
                <ObjectTypeBadge objectType={table.object_type} />
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
