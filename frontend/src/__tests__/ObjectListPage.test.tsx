import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import App from "../App";

const searchTables = vi.fn();
const fetchTableLineage = vi.fn();
const fetchLatestScanRun = vi.fn();
const createScan = vi.fn();
const fetchTableImpact = vi.fn();

vi.mock("../api", () => ({
  searchTables: (...args: unknown[]) => searchTables(...args),
  fetchTableLineage: (...args: unknown[]) => fetchTableLineage(...args),
  fetchLatestScanRun: (...args: unknown[]) => fetchLatestScanRun(...args),
  createScan: (...args: unknown[]) => createScan(...args),
  fetchTableImpact: (...args: unknown[]) => fetchTableImpact(...args),
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
  fetchLatestScanRun.mockResolvedValue({ scan_run: null });
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
