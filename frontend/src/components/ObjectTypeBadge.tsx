const OBJECT_TYPE_LABELS: Record<string, string> = {
  data_table: "数据表",
  source_table: "源表",
  source_file: "源文件",
  table_view: "表视图",
};

export function objectTypeLabel(objectType: string | undefined): string {
  return OBJECT_TYPE_LABELS[objectType ?? "data_table"] ?? "对象";
}

interface ObjectTypeBadgeProps {
  objectType?: string;
}

export function ObjectTypeBadge({ objectType }: ObjectTypeBadgeProps) {
  const resolvedType = objectType ?? "data_table";

  return (
    <span className={`object-type-badge object-type-${resolvedType}`}>
      {objectTypeLabel(resolvedType)}
    </span>
  );
}
