import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import App from "../App";

const searchTables = vi.fn();
const fetchTableLineage = vi.fn();
const fetchLatestScanRun = vi.fn();
const createScan = vi.fn();
const fetchTableImpact = vi.fn();
const fetchCycleGroups = vi.fn();

vi.mock("../api", () => ({
  searchTables: (...args: unknown[]) => searchTables(...args),
  fetchTableLineage: (...args: unknown[]) => fetchTableLineage(...args),
  fetchLatestScanRun: (...args: unknown[]) => fetchLatestScanRun(...args),
  createScan: (...args: unknown[]) => createScan(...args),
  fetchTableImpact: (...args: unknown[]) => fetchTableImpact(...args),
  fetchCycleGroups: (...args: unknown[]) => fetchCycleGroups(...args),
}));

afterEach(() => {
  cleanup();
});

beforeEach(() => {
  searchTables.mockReset();
  fetchTableLineage.mockReset();
  fetchLatestScanRun.mockReset();
  createScan.mockReset();
  fetchTableImpact.mockReset();
  fetchCycleGroups.mockReset();
  fetchLatestScanRun.mockResolvedValue({ scan_run: null });
  fetchCycleGroups.mockResolvedValue({
    summary: { group_count: 0, table_count: 0, edge_count: 0 },
    items: [],
  });
});

test("stat cards link to the filtered object list page", async () => {
  searchTables.mockResolvedValue({
    items: [
      { id: 1, key: "source_table:legacy_orders", name: "legacy_orders", object_type: "source_table" },
      { id: 2, key: "source_file:orders.xlsx", name: "orders.xlsx", object_type: "source_file" },
      { id: 3, key: "table:dm.orders", name: "dm.orders", object_type: "data_table" },
    ],
  });

  render(
    <MemoryRouter initialEntries={["/"]}>
      <App />
    </MemoryRouter>,
  );

  const sourceTableLink = await screen.findByRole("link", { name: "查看源表对象列表" });
  expect(sourceTableLink.getAttribute("href")).toBe("/objects?type=source_table");
});

test("object list page filters by type and links each object to its detail page", async () => {
  searchTables.mockResolvedValue({
    items: [
      { id: 1, key: "source_table:legacy_orders", name: "legacy_orders", object_type: "source_table" },
      { id: 2, key: "source_file:orders.xlsx", name: "orders.xlsx", object_type: "source_file" },
      { id: 3, key: "table:dm.orders", name: "dm.orders", object_type: "data_table" },
    ],
  });

  render(
    <MemoryRouter initialEntries={["/objects?type=source_table"]}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("对象列表")).toBeTruthy();
  expect(screen.getByText("当前类型：源表")).toBeTruthy();
  expect(screen.getByRole("link", { name: "legacy_orders" }).getAttribute("href")).toBe(
    "/tables/source_table%3Alegacy_orders",
  );
  expect(screen.queryByText("orders.xlsx")).toBeNull();

  fireEvent.change(screen.getByPlaceholderText("搜索对象名称"), {
    target: { value: "legacy" },
  });
  fireEvent.click(screen.getByRole("button", { name: "搜索" }));

  await waitFor(() => {
    expect(screen.getByRole("link", { name: "legacy_orders" })).toBeTruthy();
  });
});

test("cycle analysis page shows grouped closed loops and links each table to detail", async () => {
  fetchCycleGroups.mockResolvedValue({
    summary: { group_count: 2, table_count: 5, edge_count: 6 },
    items: [
      {
        group_key: "cycle_group:1",
        table_count: 3,
        edge_count: 4,
        tables: [
          {
            id: 1,
            key: "table:dm.triangle_a",
            name: "dm.triangle_a",
            object_type: "data_table",
            cycle_edge_count: 3,
          },
          {
            id: 3,
            key: "table:dm.triangle_c",
            name: "dm.triangle_c",
            object_type: "data_table",
            cycle_edge_count: 3,
          },
          {
            id: 2,
            key: "table:dm.triangle_b",
            name: "dm.triangle_b",
            object_type: "data_table",
            cycle_edge_count: 2,
          },
        ],
      },
      {
        group_key: "cycle_group:2",
        table_count: 2,
        edge_count: 2,
        tables: [
          {
            id: 4,
            key: "table:dm.loop_left",
            name: "dm.loop_left",
            object_type: "data_table",
            cycle_edge_count: 2,
          },
          {
            id: 5,
            key: "table:dm.loop_right",
            name: "dm.loop_right",
            object_type: "data_table",
            cycle_edge_count: 2,
          },
        ],
      },
    ],
  });

  render(
    <MemoryRouter initialEntries={["/analysis/cycles"]}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "闭环分析" })).toBeTruthy();
  expect(screen.getByText("闭环组数量")).toBeTruthy();
  expect(screen.getByText("闭环表总数")).toBeTruthy();
  expect(screen.getByText("组内闭环边总数")).toBeTruthy();
  expect(screen.getByText("闭环组 1")).toBeTruthy();
  expect(screen.getByText(/3 张表/)).toBeTruthy();
  expect(screen.getByText("dm.triangle_a")).toBeTruthy();
  expect(screen.getAllByText("循环边次数：3").length).toBeGreaterThan(0);
  expect(screen.getByRole("link", { name: "查看 dm.triangle_a 详情" }).getAttribute("href")).toBe(
    "/tables/table%3Adm.triangle_a",
  );
  const cycleLinks = screen.getAllByRole("link").filter((link) => link.getAttribute("href")?.startsWith("/tables/"));
  expect(cycleLinks[0]?.textContent).toBe("dm.triangle_a");
  expect(cycleLinks[1]?.textContent).toBe("dm.triangle_c");
  expect(cycleLinks[2]?.textContent).toBe("dm.triangle_b");
});
