import { RelatedObjects } from "../types";

interface RelatedObjectsPanelProps {
  relatedObjects: RelatedObjects;
}

function renderList(title: string, items: { key: string; name: string }[]) {
  return (
    <div>
      <h3>{title}</h3>
      <ul>
        {items.length === 0 ? <li>None</li> : null}
        {items.map((item) => (
          <li key={item.key}>{item.name}</li>
        ))}
      </ul>
    </div>
  );
}

export function RelatedObjectsPanel({ relatedObjects }: RelatedObjectsPanelProps) {
  // Group related objects so the detail page can show technical context at a glance.
  return (
    <section className="panel">
      <h2>Related Objects</h2>
      <div className="related-grid">
        {renderList("Jobs", relatedObjects.jobs)}
        {renderList("Java Modules", relatedObjects.java_modules)}
        {renderList("Transformations", relatedObjects.transformations)}
      </div>
    </section>
  );
}
