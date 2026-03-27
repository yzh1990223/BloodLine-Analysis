import { render } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { OverviewGraph } from "../components/OverviewGraph";

const reactFlowProps = vi.fn();

vi.mock("reactflow", () => ({
  Background: () => null,
  Controls: () => null,
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
