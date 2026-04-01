import { useMemo, useState } from "react";
import { Background, Controls, Handle, NodeProps, Position, ReactFlow } from "reactflow";
import {
  OverviewNodeData,
  buildOverviewGraph,
  focusOverviewGraph,
} from "../graph/overviewGraph";
import { TableLineageResponse } from "../types";

interface OverviewGraphProps {
  lineages: TableLineageResponse[];
  onTableSelect: (tableKey: string) => void;
}

export function OverviewObjectNode({ data }: NodeProps<OverviewNodeData>) {
  return (
    <div className="overview-object-card">
      <Handle type="target" position={Position.Left} className="overview-node-handle" />
      <div className="node-bilingual-labels">
        <strong className="node-primary-label">{data.technicalName}</strong>
        {data.technicalName !== data.label ? (
          <small className="node-secondary-label">{data.label}</small>
        ) : null}
      </div>
      <Handle type="source" position={Position.Right} className="overview-node-handle" />
    </div>
  );
}

export function OverviewGraph({
  lineages,
  onTableSelect,
}: OverviewGraphProps) {
  const [focusedTableKey, setFocusedTableKey] = useState<string | null>(null);

  const graph = useMemo(() => buildOverviewGraph(lineages), [lineages]);
  const { nodes, edges } = useMemo(
    () => focusOverviewGraph(graph, focusedTableKey),
    [focusedTableKey, graph],
  );
  const nodeTypes = useMemo(() => ({ overviewObject: OverviewObjectNode }), []);

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>全量对象总览</h2>
          <p className="panel-subtitle">首页默认展示当前已扫描出的对象级血缘关系，并标注节点类型。</p>
        </div>
        <div className="overview-legend" aria-label="图例">
          <span className="overview-legend-item overview-legend-source">源表</span>
          <span className="overview-legend-item overview-legend-middle">中间表</span>
          <span className="overview-legend-item overview-legend-sink">结果表</span>
        </div>
      </div>
      <div className="overview-flow">
        <ReactFlow
          fitView
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          zoomOnDoubleClick={false}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable
          onNodeClick={(_, node) => {
            setFocusedTableKey((current) => (current === node.id ? null : node.id));
          }}
          onNodeDoubleClick={(_, node) => onTableSelect(node.id)}
          onPaneClick={() => setFocusedTableKey(null)}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#d6dde6" gap={20} size={1} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </section>
  );
}
