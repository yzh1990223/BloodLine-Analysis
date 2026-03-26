import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchTableImpact } from "../api";
import { TableImpactResponse } from "../types";

export function ImpactPage() {
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
          setError(err instanceof Error ? err.message : "Failed to load impact");
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
        <p className="eyebrow">Impact Analysis</p>
        <h1>{impact?.table?.name ?? decodedTableKey}</h1>
        <Link to={`/tables/${encodeURIComponent(decodedTableKey)}`}>Back to table detail</Link>
      </header>

      <section className="panel">
        <h2>Impacted Tables</h2>
        <ul className="result-list">
          {impact?.impacted_tables.length ? null : <li>No downstream impact found.</li>}
          {impact?.impacted_tables.map((table) => (
            <li key={`${table.key}-${table.hop}`}>
              <span>{table.name}</span>
              <small>Hop {table.hop}</small>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
