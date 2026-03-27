import { RelatedObjects } from "../types";

interface RelatedObjectsPanelProps {
  relatedObjects: RelatedObjects;
}

function renderList(title: string, items: { key: string; name: string }[]) {
  return (
    <div>
      <h3>{title}</h3>
      <ul>
        {items.length === 0 ? <li>无</li> : null}
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
      <h2>关联对象</h2>
      <div className="related-grid">
        {renderList("作业", relatedObjects.jobs)}
        {renderList("Java 模块", relatedObjects.java_modules)}
        {renderList("转换", relatedObjects.transformations)}
      </div>
    </section>
  );
}
