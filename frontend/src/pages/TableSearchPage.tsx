import { useState } from "react";
import { Link } from "react-router-dom";
import { searchTables } from "../api";
import { SearchBar } from "../components/SearchBar";
import { TableSummary } from "../types";

export function TableSearchPage() {
  const [items, setItems] = useState<TableSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(query: string) {
    setLoading(true);
    setError(null);
    try {
      const response = await searchTables(query);
      setItems(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page">
      <header className="page-header">
        <p className="eyebrow">BloodLine Analysis</p>
        <h1>Table Search</h1>
        <p className="subtitle">Search MySQL tables and inspect lineage across Kettle and Java.</p>
      </header>

      <SearchBar onSearch={handleSearch} />

      {loading ? <p>Loading…</p> : null}
      {error ? <p className="error">{error}</p> : null}

      <section className="panel">
        <h2>Results</h2>
        <ul className="result-list">
          {items.length === 0 ? <li>No results yet.</li> : null}
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
