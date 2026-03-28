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

const searchTables = vi.fn();
const fetchTableLineage = vi.fn();

vi.mock("../api", () => ({
  searchTables: (...args: unknown[]) => searchTables(...args),
  fetchTableLineage: (...args: unknown[]) => fetchTableLineage(...args),
}));

beforeEach(() => {
  searchTables.mockReset();
  fetchTableLineage.mockReset();
});

test("table detail page renders the end-to-end lineage chain graph", async () => {
  searchTables.mockResolvedValue({
    items: [
      { id: 1, key: "source_table:legacy_orders", name: "legacy_orders", object_type: "source_table" },
      { id: 2, key: "table:dm.user_order_summary", name: "dm.user_order_summary", object_type: "data_table" },
      { id: 3, key: "table:app.order_dashboard", name: "app.order_dashboard", object_type: "data_table" },
      { id: 4, key: "table:dm.legacy_side_output", name: "dm.legacy_side_output", object_type: "data_table" },
      { id: 5, key: "table:ods.dashboard_source", name: "ods.dashboard_source", object_type: "data_table" },
    ],
  });
  fetchTableLineage.mockImplementation(async (tableKey: string) => {
    if (tableKey === "source_table:legacy_orders") {
      return {
        table: { id: 1, key: "source_table:legacy_orders", name: "legacy_orders", object_type: "source_table" },
        upstream_tables: [],
        downstream_tables: [
          { id: 2, key: "table:dm.user_order_summary", name: "dm.user_order_summary", object_type: "data_table" },
          { id: 4, key: "table:dm.legacy_side_output", name: "dm.legacy_side_output", object_type: "data_table" },
        ],
        related_objects: { jobs: [], java_modules: [], transformations: [] },
      };
    }
    if (tableKey === "table:app.order_dashboard") {
      return {
        table: { id: 3, key: "table:app.order_dashboard", name: "app.order_dashboard", object_type: "data_table" },
        upstream_tables: [
          { id: 2, key: "table:dm.user_order_summary", name: "dm.user_order_summary", object_type: "data_table" },
          { id: 5, key: "table:ods.dashboard_source", name: "ods.dashboard_source", object_type: "data_table" },
        ],
        downstream_tables: [],
        related_objects: { jobs: [], java_modules: [], transformations: [] },
      };
    }
    if (tableKey === "table:dm.legacy_side_output") {
      return {
        table: { id: 4, key: "table:dm.legacy_side_output", name: "dm.legacy_side_output", object_type: "data_table" },
        upstream_tables: [
          { id: 1, key: "source_table:legacy_orders", name: "legacy_orders", object_type: "source_table" },
        ],
        downstream_tables: [],
        related_objects: { jobs: [], java_modules: [], transformations: [] },
      };
    }
    if (tableKey === "table:ods.dashboard_source") {
      return {
        table: { id: 5, key: "table:ods.dashboard_source", name: "ods.dashboard_source", object_type: "data_table" },
        upstream_tables: [],
        downstream_tables: [
          { id: 3, key: "table:app.order_dashboard", name: "app.order_dashboard", object_type: "data_table" },
        ],
        related_objects: { jobs: [], java_modules: [], transformations: [] },
      };
    }
    return {
      table: { id: 2, key: "table:dm.user_order_summary", name: "dm.user_order_summary", object_type: "data_table" },
      upstream_tables: [
        { id: 1, key: "source_table:legacy_orders", name: "legacy_orders", object_type: "source_table" },
      ],
      downstream_tables: [
        { id: 3, key: "table:app.order_dashboard", name: "app.order_dashboard", object_type: "data_table" },
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
        transformations: [],
      },
    };
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
    expect(searchTables).toHaveBeenCalledWith("");
  });
  await waitFor(() => {
    expect(fetchTableLineage).toHaveBeenCalledWith("source_table:legacy_orders");
    expect(fetchTableLineage).toHaveBeenCalledWith("table:dm.user_order_summary");
    expect(fetchTableLineage).toHaveBeenCalledWith("table:app.order_dashboard");
  });

  expect(screen.getAllByText("legacy_orders").length).toBeGreaterThan(0);
  expect(screen.getAllByText("app.order_dashboard").length).toBeGreaterThan(0);
  expect(screen.queryByText("dm.legacy_side_output")).toBeNull();
  expect(screen.queryByText("ods.dashboard_source")).toBeNull();

  fireEvent.click(screen.getByRole("button", { name: "daily_summary_job" }));

  await waitFor(() => {
    expect(screen.getByTestId("rf__node-source_table:legacy_orders").className).toContain("detail-node-neighbor");
    expect(screen.getByTestId("rf__node-table:app.order_dashboard").className).toContain("detail-node-dim");
  });
});
