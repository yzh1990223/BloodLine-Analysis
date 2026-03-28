import { render } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { OverviewGraph, OverviewObjectNode } from "../components/OverviewGraph";

const reactFlowProps = vi.fn();
const handleProps = vi.fn();

vi.mock("reactflow", () => ({
  Background: () => null,
  Controls: () => null,
  Handle: (props: Record<string, unknown>) => {
    handleProps(props);
    return <div data-testid={`handle-${String(props.type)}`} />;
  },
  Position: {
    Left: "left",
    Right: "right",
  },
  ReactFlow: (props: Record<string, unknown>) => {
    reactFlowProps(props);
    return <div data-testid="react-flow" />;
  },
}));

test("disables canvas zoom on double click so node double click can open detail", () => {
  render(
    <OverviewGraph
      lineages={[
        {
          table: { id: 1, key: "table:ods.orders", name: "ods.orders" },
          upstream_tables: [],
          downstream_tables: [],
          related_objects: { jobs: [], java_modules: [], transformations: [] },
        },
      ]}
      onTableSelect={() => {}}
    />,
  );

  expect(reactFlowProps).toHaveBeenCalled();
  expect(reactFlowProps.mock.calls[0]?.[0]?.zoomOnDoubleClick).toBe(false);
});

test("renders source and target handles for custom overview nodes", () => {
  render(
    <OverviewObjectNode
      id="table:ods.orders"
      data={{
        key: "table:ods.orders",
        label: "ods.orders",
        role: "source",
        objectType: "data_table",
      }}
      selected={false}
      xPos={0}
      yPos={0}
      dragging={false}
      zIndex={0}
      isConnectable={false}
      type="overviewObject"
    />,
  );

  expect(handleProps).toHaveBeenCalledTimes(2);
  expect(handleProps.mock.calls[0]?.[0]?.type).toBe("target");
  expect(handleProps.mock.calls[1]?.[0]?.type).toBe("source");
});
