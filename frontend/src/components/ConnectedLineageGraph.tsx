import { useEffect, useMemo, useState } from "react";
import { Handle, NodeProps, Position, ReactFlow } from "reactflow";
import {
  OverviewNodeData,
} from "./OverviewGraph";
import {
  buildOverviewGraph,
} from "../graph/overviewGraph";
import { TableLineageResponse } from "../types";

interface ConnectedLineageGraphProps {
  currentTableKey: string;
  lineages: TableLineageResponse[];
  onTableSelect: (tableKey: string) => void;
  highlightedTableKeys?: string[];
}

function DetailLineageNode({ data }: NodeProps<OverviewNodeData>) {
  const sourceHandles = data.sourceHandles?.length ? data.sourceHandles : ["source-0"];
  const targetHandles = data.targetHandles?.length ? data.targetHandles : ["target-0"];

  return (
    <div
      className="detail-lineage-card"
      title={data.label}
      style={data.nodeHeight ? { minHeight: `${data.nodeHeight}px` } : undefined}
    >
      {targetHandles.map((handleId, index) => (
        <Handle
          key={handleId}
          id={handleId}
          type="target"
          position={Position.Left}
          className="overview-node-handle detail-node-handle"
          style={{ top: `${((index + 1) / (targetHandles.length + 1)) * 100}%` }}
        />
      ))}
      <strong>{data.label}</strong>
      {sourceHandles.map((handleId, index) => (
        <Handle
          key={handleId}
          id={handleId}
          type="source"
          position={Position.Right}
          className="overview-node-handle detail-node-handle"
          style={{ top: `${((index + 1) / (sourceHandles.length + 1)) * 100}%` }}
        />
      ))}
    </div>
  );
}

export function ConnectedLineageGraph({
  currentTableKey,
  lineages,
  onTableSelect,
  highlightedTableKeys = [],
}: ConnectedLineageGraphProps) {
  const [focusedTableKey, setFocusedTableKey] = useState<string | null>(currentTableKey);

  useEffect(() => {
    setFocusedTableKey(currentTableKey);
  }, [currentTableKey]);

  const graph = useMemo(
    () =>
      buildOverviewGraph(lineages, {
        columnGap: 320,
        rowGap: 104,
        edgeColor: "#c7cdd6",
        edgeWidth: 1.2,
        separateHandles: true,
        edgeType: "default",
      }),
    [lineages],
  );
  const { nodes, edges } = useMemo(() => {
    const relatedSelection = new Set(highlightedTableKeys);
    const neighborIds = new Set<string>();
    const highlightedEdgeIds = new Set<string>();

    if (relatedSelection.size > 0) {
      for (const edge of graph.edges) {
        if (relatedSelection.has(edge.source) && relatedSelection.has(edge.target)) {
          highlightedEdgeIds.add(edge.id);
        }
      }
    } else if (focusedTableKey) {
      neighborIds.add(focusedTableKey);
      for (const edge of graph.edges) {
        if (edge.source === focusedTableKey || edge.target === focusedTableKey) {
          neighborIds.add(edge.source);
          neighborIds.add(edge.target);
          highlightedEdgeIds.add(edge.id);
        }
      }
    }

    return {
      nodes: graph.nodes.map((node) => ({
        ...node,
        className: [
          node.className ?? "",
          relatedSelection.size > 0
            ? relatedSelection.has(node.id)
              ? "detail-node-neighbor"
              : "detail-node-dim"
            : focusedTableKey
            ? node.id === focusedTableKey
              ? "detail-node-selected"
              : neighborIds.has(node.id)
                ? "detail-node-neighbor"
                : "detail-node-dim"
            : "",
        ]
          .filter(Boolean)
          .join(" "),
      })),
      edges: graph.edges.map((edge) => ({
        ...edge,
        className: relatedSelection.size > 0
          ? highlightedEdgeIds.has(edge.id)
            ? "detail-edge-highlighted"
            : "detail-edge-dim"
          : focusedTableKey
          ? highlightedEdgeIds.has(edge.id)
            ? "detail-edge-highlighted"
            : "detail-edge-dim"
          : "",
      })),
    };
  }, [focusedTableKey, graph, highlightedTableKeys]);
  const nodeTypes = useMemo(() => ({ overviewObject: DetailLineageNode }), []);

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>完整链路图</h2>
          <p className="panel-subtitle">从左到右展示当前对象所在的完整处理链路，单击节点高亮，双击可进入对应详情页。</p>
        </div>
      </div>
      <div className="overview-flow detail-overview-flow">
        <ReactFlow
          fitView
          fitViewOptions={{ padding: 0.2 }}
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          zoomOnDoubleClick={false}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable
          minZoom={0.35}
          maxZoom={1.3}
          onNodeClick={(_, node) => {
            setFocusedTableKey((current) => (current === node.id ? null : node.id));
          }}
          onNodeDoubleClick={(_, node) => onTableSelect(node.id)}
          onPaneClick={() => setFocusedTableKey(currentTableKey)}
          proOptions={{ hideAttribution: true }}
        />
      </div>
    </section>
  );
}
