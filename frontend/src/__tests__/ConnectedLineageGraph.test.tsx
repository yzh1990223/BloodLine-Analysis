import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { ConnectedLineageGraph } from "../components/ConnectedLineageGraph";

const reactFlowProps = vi.fn();

vi.mock("reactflow", () => ({
  Handle: () => <div data-testid="handle" />,
  Position: {
    Left: "left",
    Right: "right",
  },
  ReactFlow: (props: Record<string, unknown>) => {
    reactFlowProps(props);
    return <div data-testid="react-flow" />;
  },
}));

test("connected lineage graph renders api endpoint nodes with oval styling", () => {
  render(
    <ConnectedLineageGraph
      currentTableKey="table:dm.user_info"
      onTableSelect={() => {}}
      lineages={[
        {
          table: {
            id: 1,
            key: "table:dm.user_info",
            name: "dm.user_info",
            object_type: "data_table",
          },
          upstream_tables: [],
          downstream_tables: [
            {
              id: 2,
              key: "api:GET /users",
              name: "GET /users",
              object_type: "api_endpoint",
            },
          ],
          related_objects: { jobs: [], java_modules: [], api_endpoints: [], transformations: [] },
        },
        {
          table: {
            id: 2,
            key: "api:GET /users",
            name: "GET /users",
            object_type: "api_endpoint",
          },
          upstream_tables: [
            {
              id: 1,
              key: "table:dm.user_info",
              name: "dm.user_info",
              object_type: "data_table",
            },
          ],
          downstream_tables: [],
          related_objects: { jobs: [], java_modules: [], api_endpoints: [], transformations: [] },
        },
      ]}
    />,
  );

  expect(reactFlowProps).toHaveBeenCalled();
  const props = reactFlowProps.mock.calls[0]?.[0] as {
    nodes: Array<{ id: string; data: { objectType: string } }>;
    nodeTypes: Record<string, (props: { data: { objectType: string; technicalName: string; label: string } }) => any>;
  };
  const apiNode = props.nodes.find((node) => node.id === "api:GET /users");
  expect(apiNode?.data.objectType).toBe("api_endpoint");
  expect(apiNode?.className).toContain("detail-node-api");

  const OverviewObject = props.nodeTypes.overviewObject;
  const { container } = render(
    <OverviewObject
      data={{
        ...apiNode!.data,
        technicalName: "GET /users",
        label: "GET /users",
      }}
    />,
  );

  expect(container.querySelector(".detail-lineage-card-api")).toBeTruthy();
});
