import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import { TableDetailPage } from "../pages/TableDetailPage";

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

vi.stubGlobal("ResizeObserver", ResizeObserverMock);

const fetchConnectedLineage = vi.fn();

vi.mock("../api", () => ({
  fetchConnectedLineage: (...args: unknown[]) => fetchConnectedLineage(...args),
}));

beforeEach(() => {
  fetchConnectedLineage.mockReset();
});

test("table detail page renders the end-to-end lineage chain graph", async () => {
  fetchConnectedLineage.mockResolvedValue({
    table_lineage: {
      table: {
        id: 2,
        key: "table:dm.user_order_summary",
        name: "dm.user_order_summary",
        display_name: "用户订单汇总表",
        object_type: "data_table",
      },
      upstream_tables: [
        {
          id: 1,
          key: "source_table:legacy_orders",
          name: "legacy_orders",
          display_name: "历史订单源表",
          object_type: "source_table",
        },
      ],
      downstream_tables: [
        {
          id: 3,
          key: "table:app.order_dashboard",
          name: "app.order_dashboard",
          display_name: "订单看板表",
          object_type: "data_table",
        },
        { id: 30, key: "api:GET /api/orders/{id}", name: "GET /api/orders/{id}", object_type: "api_endpoint" },
      ],
      related_objects: {
        jobs: [
          {
            id: 10,
            key: "job:daily_summary_job",
            name: "daily_summary_job",
            related_table_keys: [
              "source_table:legacy_orders",
              "table:dm.user_order_summary",
            ],
          },
        ],
        java_modules: [],
        api_endpoints: [
          {
            id: 30,
            key: "api:GET /api/orders/{id}",
            name: "GET /api/orders/{id}",
            related_table_keys: ["table:dm.user_order_summary"],
          },
        ],
        transformations: [],
      },
    },
    items: [
      {
        table: {
          id: 1,
          key: "source_table:legacy_orders",
          name: "legacy_orders",
          display_name: "历史订单源表",
          object_type: "source_table",
        },
        upstream_tables: [],
        downstream_tables: [
          {
            id: 2,
            key: "table:dm.user_order_summary",
            name: "dm.user_order_summary",
            display_name: "用户订单汇总表",
            object_type: "data_table",
          },
        ],
        related_objects: { jobs: [], java_modules: [], api_endpoints: [], transformations: [] },
      },
      {
        table: {
          id: 2,
          key: "table:dm.user_order_summary",
          name: "dm.user_order_summary",
          display_name: "用户订单汇总表",
          object_type: "data_table",
        },
        upstream_tables: [
          {
            id: 1,
            key: "source_table:legacy_orders",
            name: "legacy_orders",
            display_name: "历史订单源表",
            object_type: "source_table",
          },
        ],
        downstream_tables: [
          {
            id: 3,
            key: "table:app.order_dashboard",
            name: "app.order_dashboard",
            display_name: "订单看板表",
            object_type: "data_table",
          },
          { id: 30, key: "api:GET /api/orders/{id}", name: "GET /api/orders/{id}", object_type: "api_endpoint" },
        ],
        related_objects: {
          jobs: [
            {
              id: 10,
              key: "job:daily_summary_job",
              name: "daily_summary_job",
              related_table_keys: [
                "source_table:legacy_orders",
                "table:dm.user_order_summary",
              ],
            },
          ],
          java_modules: [],
          api_endpoints: [
            {
              id: 30,
              key: "api:GET /api/orders/{id}",
              name: "GET /api/orders/{id}",
              related_table_keys: ["table:dm.user_order_summary"],
            },
          ],
          transformations: [],
        },
      },
      {
        table: {
          id: 3,
          key: "table:app.order_dashboard",
          name: "app.order_dashboard",
          display_name: "订单看板表",
          object_type: "data_table",
        },
        upstream_tables: [
          {
            id: 2,
            key: "table:dm.user_order_summary",
            name: "dm.user_order_summary",
            display_name: "用户订单汇总表",
            object_type: "data_table",
          },
        ],
        downstream_tables: [],
        related_objects: { jobs: [], java_modules: [], api_endpoints: [], transformations: [] },
      },
    ],
  });

  render(
    <MemoryRouter initialEntries={["/tables/table%3Adm.user_order_summary"]}>
      <Routes>
        <Route path="/tables/:tableKey" element={<TableDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );

  expect(await screen.findByText("完整链路图")).toBeTruthy();
  await waitFor(() => {
    expect(fetchConnectedLineage).toHaveBeenCalledWith("table:dm.user_order_summary");
  });

  expect(screen.getAllByText("legacy_orders").length).toBeGreaterThan(0);
  expect(screen.getAllByText("历史订单源表").length).toBeGreaterThan(0);
  expect(screen.getAllByText("app.order_dashboard").length).toBeGreaterThan(0);
  expect(screen.getAllByText("订单看板表").length).toBeGreaterThan(0);
  expect(screen.getAllByText("GET /api/orders/{id}").length).toBeGreaterThan(0);
  expect(screen.queryByText("dm.legacy_side_output")).toBeNull();
  expect(screen.queryByText("ods.dashboard_source")).toBeNull();
  expect(screen.getByRole("button", { name: "GET /api/orders/{id}" })).toBeTruthy();

  fireEvent.click(screen.getByRole("button", { name: "daily_summary_job" }));

  await waitFor(() => {
    expect(screen.getByTestId("rf__node-source_table:legacy_orders").className).toContain("detail-node-neighbor");
    expect(screen.getByTestId("rf__node-table:app.order_dashboard").className).toContain("detail-node-dim");
  });
});
