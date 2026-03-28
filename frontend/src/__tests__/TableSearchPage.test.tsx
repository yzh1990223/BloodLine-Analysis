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

vi.mock("../api", () => ({
  searchTables: (...args: unknown[]) => searchTables(...args),
  fetchTableLineage: (...args: unknown[]) => fetchTableLineage(...args),
  fetchLatestScanRun: (...args: unknown[]) => fetchLatestScanRun(...args),
  createScan: (...args: unknown[]) => createScan(...args),
}));

beforeEach(() => {
  searchTables.mockReset();
  fetchTableLineage.mockReset();
  fetchLatestScanRun.mockReset();
  createScan.mockReset();
  fetchLatestScanRun.mockResolvedValue({ scan_run: null });
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
