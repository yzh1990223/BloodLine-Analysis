import { expect, test } from "vitest";
import { buildOverviewGraph, focusOverviewGraph } from "../graph/overviewGraph";
import { TableLineageResponse } from "../types";

test("buildOverviewGraph creates unique table nodes and downstream edges", () => {
  const lineages: TableLineageResponse[] = [
    {
      table: { id: 1, key: "table:ods.orders", name: "ods.orders" },
      upstream_tables: [],
      downstream_tables: [
        {
          id: 2,
          key: "table:dm.user_order_summary",
          name: "dm.user_order_summary",
        },
      ],
      related_objects: { jobs: [], java_modules: [], transformations: [] },
    },
    {
      table: {
        id: 2,
        key: "table:dm.user_order_summary",
        name: "dm.user_order_summary",
      },
      upstream_tables: [{ id: 1, key: "table:ods.orders", name: "ods.orders" }],
      downstream_tables: [
        {
          id: 3,
          key: "table:app.order_dashboard",
          name: "app.order_dashboard",
        },
      ],
      related_objects: { jobs: [], java_modules: [], transformations: [] },
    },
  ];

  const graph = buildOverviewGraph(lineages);

  expect(graph.nodes.map((node) => node.data.label)).toEqual([
    "ods.orders",
    "dm.user_order_summary",
    "app.order_dashboard",
  ]);
  expect(graph.edges.map((edge) => edge.id).sort()).toEqual(
    [
      "table:ods.orders->table:dm.user_order_summary",
      "table:dm.user_order_summary->table:app.order_dashboard",
    ].sort(),
  );
  const sourceNode = graph.nodes.find((node) => node.id === "table:ods.orders");
  const middleNode = graph.nodes.find(
    (node) => node.id === "table:dm.user_order_summary",
  );
  const sinkNode = graph.nodes.find(
    (node) => node.id === "table:app.order_dashboard",
  );

  expect(sourceNode?.className).toContain("overview-node-source");
  expect(middleNode?.className).toContain("overview-node-middle");
  expect(sinkNode?.className).toContain("overview-node-sink");
  expect((middleNode?.position.x ?? 0) - (sourceNode?.position.x ?? 0)).toBeGreaterThanOrEqual(
    320,
  );
});

test("focusOverviewGraph highlights the selected node and its direct neighbors", () => {
  const lineages: TableLineageResponse[] = [
    {
      table: { id: 1, key: "table:ods.orders", name: "ods.orders" },
      upstream_tables: [],
      downstream_tables: [
        {
          id: 2,
          key: "table:dm.user_order_summary",
          name: "dm.user_order_summary",
        },
      ],
      related_objects: { jobs: [], java_modules: [], transformations: [] },
    },
    {
      table: {
        id: 2,
        key: "table:dm.user_order_summary",
        name: "dm.user_order_summary",
      },
      upstream_tables: [{ id: 1, key: "table:ods.orders", name: "ods.orders" }],
      downstream_tables: [
        {
          id: 3,
          key: "table:app.order_dashboard",
          name: "app.order_dashboard",
        },
      ],
      related_objects: { jobs: [], java_modules: [], transformations: [] },
    },
  ];

  const graph = buildOverviewGraph(lineages);
  const focused = focusOverviewGraph(graph, "table:dm.user_order_summary");

  const selectedNode = focused.nodes.find(
    (node) => node.id === "table:dm.user_order_summary",
  );
  const upstreamNode = focused.nodes.find((node) => node.id === "table:ods.orders");
  const downstreamNode = focused.nodes.find(
    (node) => node.id === "table:app.order_dashboard",
  );

  expect(selectedNode?.className).toContain("overview-node-selected");
  expect(upstreamNode?.className).toContain("overview-node-neighbor");
  expect(downstreamNode?.className).toContain("overview-node-neighbor");
  expect(
    focused.edges.find((edge) => edge.id === "table:ods.orders->table:dm.user_order_summary")
      ?.className,
  ).toContain("overview-edge-highlighted");
  expect(
    focused.edges.find(
      (edge) => edge.id === "table:dm.user_order_summary->table:app.order_dashboard",
    )?.className,
  ).toContain("overview-edge-highlighted");
});
