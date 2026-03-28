import { RelatedObjects } from "../types";

interface RelatedObjectsPanelProps {
  relatedObjects: RelatedObjects;
  activeObjectKey?: string | null;
  onObjectSelect?: (objectKey: string | null, relatedTableKeys: string[]) => void;
}

function renderList(
  title: string,
  items: { key: string; name: string; related_table_keys?: string[] }[],
  activeObjectKey?: string | null,
  onObjectSelect?: (objectKey: string | null, relatedTableKeys: string[]) => void,
) {
  return (
    <div>
      <h3>{title}</h3>
      <ul>
        {items.length === 0 ? <li>无</li> : null}
        {items.map((item) => (
          <li key={item.key}>
            <button
              type="button"
              className={`related-object-button${activeObjectKey === item.key ? " is-active" : ""}`}
              onClick={() =>
                onObjectSelect?.(
                  activeObjectKey === item.key ? null : item.key,
                  item.related_table_keys ?? [],
                )
              }
            >
              {item.name}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function RelatedObjectsPanel({
  relatedObjects,
  activeObjectKey,
  onObjectSelect,
}: RelatedObjectsPanelProps) {
  // Group related objects so the detail page can show technical context at a glance.
  return (
    <section className="panel">
      <h2>关联对象</h2>
      <div className="related-grid">
        {renderList("作业", relatedObjects.jobs, activeObjectKey, onObjectSelect)}
        {renderList("Java 模块", relatedObjects.java_modules, activeObjectKey, onObjectSelect)}
        {renderList("转换", relatedObjects.transformations, activeObjectKey, onObjectSelect)}
      </div>
    </section>
  );
}
