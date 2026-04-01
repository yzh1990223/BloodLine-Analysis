import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import { TableSearchPage } from "../pages/TableSearchPage";

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

vi.stubGlobal("ResizeObserver", ResizeObserverMock);

const searchTables = vi.fn();
const fetchTableLineage = vi.fn();
const fetchLatestScanRun = vi.fn();
const createScan = vi.fn();
const fetchCycleGroups = vi.fn();

vi.mock("../api", () => ({
  searchTables: (...args: unknown[]) => searchTables(...args),
  fetchTableLineage: (...args: unknown[]) => fetchTableLineage(...args),
  fetchLatestScanRun: (...args: unknown[]) => fetchLatestScanRun(...args),
  createScan: (...args: unknown[]) => createScan(...args),
  fetchCycleGroups: (...args: unknown[]) => fetchCycleGroups(...args),
}));

beforeEach(() => {
  searchTables.mockReset();
  fetchTableLineage.mockReset();
  fetchLatestScanRun.mockReset();
  createScan.mockReset();
  fetchCycleGroups.mockReset();
  fetchLatestScanRun.mockResolvedValue({ scan_run: null });
  fetchCycleGroups.mockResolvedValue({
    summary: { group_count: 3, table_count: 8, edge_count: 11 },
    items: [],
  });
});

test("loads overview stats on first render and only fetches lineage when an item is selected", async () => {
  searchTables.mockResolvedValue({
    items: [
      { id: 1, key: "table:ods.orders", name: "ods.orders", object_type: "data_table" },
      {
        id: 2,
        key: "table:dm.user_order_summary",
        name: "dm.user_order_summary",
        object_type: "data_table",
      },
      {
        id: 3,
        key: "view:dm.user_order_dashboard",
        name: "dm.user_order_dashboard",
        object_type: "table_view",
      },
      {
        id: 4,
        key: "api:GET /api/orders/summary",
        name: "GET /api/orders/summary",
        object_type: "api_endpoint",
      },
    ],
  });
  fetchTableLineage.mockResolvedValue({
    table: { id: 1, key: "table:ods.orders", name: "ods.orders", object_type: "data_table" },
    upstream_tables: [],
    downstream_tables: [
      {
        id: 2,
        key: "table:dm.user_order_summary",
        name: "dm.user_order_summary",
        object_type: "data_table",
      },
    ],
    related_objects: { jobs: [], java_modules: [], transformations: [] },
  });

  render(
    <MemoryRouter>
      <TableSearchPage />
    </MemoryRouter>,
  );

  expect(screen.getByPlaceholderText("搜索数据表")).toBeTruthy();

  await waitFor(() => {
    expect(searchTables).toHaveBeenCalledWith("");
  });
  expect(await screen.findByText("对象概览")).toBeTruthy();
  expect(screen.getByText("总对象数")).toBeTruthy();
  expect(screen.getByText("闭环分析")).toBeTruthy();
  expect(screen.getByText("数据视图")).toBeTruthy();
  expect(screen.getByRole("link", { name: "查看数据视图对象列表" }).getAttribute("href")).toBe(
    "/objects?type=table_view",
  );
  expect(screen.getByText("API接口")).toBeTruthy();
  expect(screen.getByRole("link", { name: "查看 API 接口对象列表" }).getAttribute("href")).toBe(
    "/objects?type=api_endpoint",
  );
  expect(screen.getAllByText("4").length).toBeGreaterThan(0);
  expect(fetchTableLineage).not.toHaveBeenCalled();

  fireEvent.change(screen.getByPlaceholderText("搜索数据表"), {
    target: { value: "orders" },
  });
  fireEvent.click(screen.getByRole("button", { name: "搜索" }));

  await waitFor(() => {
    expect(searchTables).toHaveBeenCalledWith("orders");
  });
  fireEvent.click(screen.getByRole("button", { name: "预览 ods.orders" }));

  await waitFor(() => {
    expect(fetchTableLineage).toHaveBeenCalledWith("table:ods.orders");
  });
  expect(await screen.findByText("局部血缘预览")).toBeTruthy();
});
