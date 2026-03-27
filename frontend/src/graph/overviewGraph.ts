import { Edge, MarkerType, Node, Position } from "reactflow";
import { TableLineageResponse } from "../types";

export interface OverviewNodeData {
  key: string;
  label: string;
  role: "source" | "middle" | "sink";
}

export interface OverviewGraphElements {
  nodes: Node<OverviewNodeData>[];
  edges: Edge[];
}

const COLUMN_GAP = 360;
const ROW_GAP = 140;

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
): OverviewGraphElements {
  const tableNames = new Map<string, string>();
  const edgePairs = new Set<string>();
  const incomingCount = new Map<string, number>();
  const outgoingCount = new Map<string, number>();

  for (const lineage of lineages) {
    if (lineage.table) {
      tableNames.set(lineage.table.key, lineage.table.name);
    }
    for (const upstream of lineage.upstream_tables) {
      tableNames.set(upstream.key, upstream.name);
    }
    for (const downstream of lineage.downstream_tables) {
      tableNames.set(downstream.key, downstream.name);
      if (lineage.table) {
        const edgeId = `${lineage.table.key}->${downstream.key}`;
        edgePairs.add(edgeId);
        outgoingCount.set(lineage.table.key, (outgoingCount.get(lineage.table.key) ?? 0) + 1);
        incomingCount.set(downstream.key, (incomingCount.get(downstream.key) ?? 0) + 1);
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
      nodes.push({
        id: key,
        type: "default",
        data: { key, label: tableNames.get(key) ?? key, role },
        position: { x: level * COLUMN_GAP, y: index * ROW_GAP },
        draggable: false,
        selectable: true,
        connectable: false,
        className: `overview-node overview-node-${role}`,
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      });
    });
  }

  const edges: Edge[] = Array.from(edgePairs)
    .sort((left, right) => left.localeCompare(right))
    .map((pair) => {
      const [source, target] = pair.split("->");
      return {
        id: pair,
        source,
        target,
        animated: false,
        type: "smoothstep",
        zIndex: 0,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 22,
          height: 22,
          color: "#24627f",
        },
        style: {
          stroke: "#24627f",
          strokeWidth: 2.2,
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
