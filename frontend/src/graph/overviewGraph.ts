import { Edge, MarkerType, Node, Position } from "reactflow";
import { TableLineageResponse } from "../types";

export interface OverviewNodeData {
  key: string;
  label: string;
  technicalName: string;
  role: "source" | "middle" | "sink";
  objectType: string;
  level: number;
  sourceHandles?: string[];
  targetHandles?: string[];
  nodeHeight?: number;
}

export interface OverviewGraphElements {
  nodes: Node<OverviewNodeData>[];
  edges: Edge[];
}

const COLUMN_GAP = 360;
const ROW_GAP = 140;

interface BuildOverviewGraphOptions {
  columnGap?: number;
  rowGap?: number;
  edgeColor?: string;
  edgeWidth?: number;
  separateHandles?: boolean;
  edgeType?: Edge["type"];
}

function isApiEndpoint(objectType: string | undefined) {
  return objectType === "api_endpoint";
}

function normalizeEdgeDirection(
  sourceKey: string,
  targetKey: string,
  objectTypes: Map<string, string>,
): [string, string] {
  const sourceType = objectTypes.get(sourceKey);
  const targetType = objectTypes.get(targetKey);

  if (isApiEndpoint(sourceType) && !isApiEndpoint(targetType)) {
    return [targetKey, sourceKey];
  }

  return [sourceKey, targetKey];
}

function classifyNodeRole(
  key: string,
  incomingCount: Map<string, number>,
  outgoingCount: Map<string, number>,
): OverviewNodeData["role"] {
  const incoming = incomingCount.get(key) ?? 0;
  const outgoing = outgoingCount.get(key) ?? 0;

  if (incoming === 0 && outgoing > 0) {
    return "source";
  }
  if (incoming > 0 && outgoing === 0) {
    return "sink";
  }
  return "middle";
}

function collectLevelByNode(edgePairs: Array<[string, string]>, nodeKeys: string[]) {
  const outgoing = new Map<string, string[]>();
  const indegree = new Map<string, number>();
  const levelByNode = new Map<string, number>();

  for (const key of nodeKeys) {
    outgoing.set(key, []);
    indegree.set(key, 0);
    levelByNode.set(key, 0);
  }

  for (const [source, target] of edgePairs) {
    outgoing.get(source)?.push(target);
    indegree.set(target, (indegree.get(target) ?? 0) + 1);
  }

  const queue = nodeKeys.filter((key) => (indegree.get(key) ?? 0) === 0);
  while (queue.length > 0) {
    const current = queue.shift();
    if (!current) {
      continue;
    }
    const currentLevel = levelByNode.get(current) ?? 0;
    for (const next of outgoing.get(current) ?? []) {
      levelByNode.set(next, Math.max(levelByNode.get(next) ?? 0, currentLevel + 1));
      indegree.set(next, (indegree.get(next) ?? 1) - 1);
      if ((indegree.get(next) ?? 0) === 0) {
        queue.push(next);
      }
    }
  }

  return levelByNode;
}

export function buildOverviewGraph(
  lineages: TableLineageResponse[],
  options: BuildOverviewGraphOptions = {},
): OverviewGraphElements {
  const columnGap = options.columnGap ?? COLUMN_GAP;
  const rowGap = options.rowGap ?? ROW_GAP;
  const edgeColor = options.edgeColor ?? "#24627f";
  const edgeWidth = options.edgeWidth ?? 2.2;
  const separateHandles = options.separateHandles ?? false;
  const edgeType = options.edgeType ?? "smoothstep";
  const tableNames = new Map<string, string>();
  const displayNames = new Map<string, string>();
  const objectTypes = new Map<string, string>();
  const edgePairs = new Set<string>();
  const incomingCount = new Map<string, number>();
  const outgoingCount = new Map<string, number>();

  for (const lineage of lineages) {
    if (lineage.table) {
      tableNames.set(lineage.table.key, lineage.table.name);
      displayNames.set(lineage.table.key, lineage.table.display_name ?? lineage.table.name);
      objectTypes.set(lineage.table.key, lineage.table.object_type ?? "data_table");
    }
    for (const upstream of lineage.upstream_tables) {
      tableNames.set(upstream.key, upstream.name);
      displayNames.set(upstream.key, upstream.display_name ?? upstream.name);
      objectTypes.set(upstream.key, upstream.object_type ?? "data_table");
    }
    for (const downstream of lineage.downstream_tables) {
      tableNames.set(downstream.key, downstream.name);
      displayNames.set(downstream.key, downstream.display_name ?? downstream.name);
      objectTypes.set(downstream.key, downstream.object_type ?? "data_table");
      if (lineage.table) {
        const [normalizedSource, normalizedTarget] = normalizeEdgeDirection(
          lineage.table.key,
          downstream.key,
          objectTypes,
        );
        const edgeId = `${normalizedSource}->${normalizedTarget}`;
        edgePairs.add(edgeId);
        outgoingCount.set(normalizedSource, (outgoingCount.get(normalizedSource) ?? 0) + 1);
        incomingCount.set(normalizedTarget, (incomingCount.get(normalizedTarget) ?? 0) + 1);
      }
    }
  }

  const nodeKeys = Array.from(tableNames.keys()).sort((left, right) => {
    const leftName = tableNames.get(left) ?? left;
    const rightName = tableNames.get(right) ?? right;
    return leftName.localeCompare(rightName);
  });
  const levels = collectLevelByNode(
    Array.from(edgePairs, (pair) => {
      const [source, target] = pair.split("->");
      return [source, target] as [string, string];
    }),
    nodeKeys,
  );

  const keysByLevel = new Map<number, string[]>();
  for (const key of nodeKeys) {
    const level = levels.get(key) ?? 0;
    const levelKeys = keysByLevel.get(level) ?? [];
    levelKeys.push(key);
    keysByLevel.set(level, levelKeys);
  }

  const sortedEdgePairs = Array.from(edgePairs).sort((left, right) => left.localeCompare(right));
  const sourceHandlesByNode = new Map<string, string[]>();
  const targetHandlesByNode = new Map<string, string[]>();
  for (const pair of sortedEdgePairs) {
    const [source, target] = pair.split("->");
    const sourceHandles = sourceHandlesByNode.get(source) ?? [];
    const targetHandles = targetHandlesByNode.get(target) ?? [];
    sourceHandles.push(`source-${sourceHandles.length}`);
    targetHandles.push(`target-${targetHandles.length}`);
    sourceHandlesByNode.set(source, sourceHandles);
    targetHandlesByNode.set(target, targetHandles);
  }

  const nodes: Node<OverviewNodeData>[] = [];
  for (const [level, keys] of Array.from(keysByLevel.entries()).sort(
    ([left], [right]) => left - right,
  )) {
    keys.sort((left, right) => {
      const leftName = tableNames.get(left) ?? left;
      const rightName = tableNames.get(right) ?? right;
      return leftName.localeCompare(rightName);
    });
    keys.forEach((key, index) => {
      const role = classifyNodeRole(key, incomingCount, outgoingCount);
      const sourceHandles = sourceHandlesByNode.get(key) ?? [];
      const targetHandles = targetHandlesByNode.get(key) ?? [];
      const handleCount = Math.max(sourceHandles.length, targetHandles.length, 1);
      nodes.push({
        id: key,
        type: "overviewObject",
        data: {
          key,
          label: displayNames.get(key) ?? tableNames.get(key) ?? key,
          technicalName: tableNames.get(key) ?? key,
          role,
          objectType: objectTypes.get(key) ?? "data_table",
          level,
          sourceHandles,
          targetHandles,
          nodeHeight: separateHandles ? Math.max(42, 18 + handleCount * 12) : undefined,
        },
        position: { x: level * columnGap, y: index * rowGap },
        draggable: false,
        selectable: true,
        connectable: false,
        className: `overview-node overview-node-${role} overview-node-level-${level % 6}`,
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      });
    });
  }

  const sourceHandleCursor = new Map<string, number>();
  const targetHandleCursor = new Map<string, number>();
  const edges: Edge[] = sortedEdgePairs.map((pair) => {
      const [source, target] = pair.split("->");
      const isApiEdge = isApiEndpoint(objectTypes.get(source)) || isApiEndpoint(objectTypes.get(target));
      const sourceIndex = sourceHandleCursor.get(source) ?? 0;
      const targetIndex = targetHandleCursor.get(target) ?? 0;
      sourceHandleCursor.set(source, sourceIndex + 1);
      targetHandleCursor.set(target, targetIndex + 1);
      return {
        id: pair,
        source,
        target,
        sourceHandle: separateHandles ? `source-${sourceIndex}` : undefined,
        targetHandle: separateHandles ? `target-${targetIndex}` : undefined,
        animated: false,
        type: edgeType,
        zIndex: 0,
        markerEnd: isApiEdge
          ? undefined
          : {
              type: MarkerType.ArrowClosed,
              width: 22,
              height: 22,
              color: edgeColor,
            },
        style: {
          stroke: edgeColor,
          strokeWidth: edgeWidth,
          strokeDasharray: isApiEdge ? "8 6" : undefined,
        },
      };
    });

  return { nodes, edges };
}

export function focusOverviewGraph(
  graph: OverviewGraphElements,
  selectedNodeId: string | null,
): OverviewGraphElements {
  if (!selectedNodeId) {
    return graph;
  }

  const neighborIds = new Set<string>([selectedNodeId]);
  const highlightedEdgeIds = new Set<string>();

  for (const edge of graph.edges) {
    if (edge.source === selectedNodeId || edge.target === selectedNodeId) {
      neighborIds.add(edge.source);
      neighborIds.add(edge.target);
      highlightedEdgeIds.add(edge.id);
    }
  }

  return {
    nodes: graph.nodes.map((node) => {
      const baseClassName = node.className ?? "";
      let className = `${baseClassName} overview-node-muted`.trim();

      if (node.id === selectedNodeId) {
        className = `${baseClassName} overview-node-selected`.trim();
      } else if (neighborIds.has(node.id)) {
        className = `${baseClassName} overview-node-neighbor`.trim();
      }

      return {
        ...node,
        className,
      };
    }),
    edges: graph.edges.map((edge) => ({
      ...edge,
      className: highlightedEdgeIds.has(edge.id)
        ? "overview-edge-highlighted"
        : "overview-edge-muted",
    })),
  };
}
