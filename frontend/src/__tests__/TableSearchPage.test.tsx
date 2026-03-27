import { render, screen, waitFor } from "@testing-library/react";
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

vi.mock("../api", () => ({
  searchTables: (...args: unknown[]) => searchTables(...args),
  fetchTableLineage: (...args: unknown[]) => fetchTableLineage(...args),
}));

beforeEach(() => {
  searchTables.mockReset();
  fetchTableLineage.mockReset();
});

test("loads the default overview graph on first render", async () => {
  searchTables.mockResolvedValue({
    items: [
      { id: 1, key: "table:ods.orders", name: "ods.orders" },
      {
        id: 2,
        key: "table:dm.user_order_summary",
        name: "dm.user_order_summary",
      },
    ],
  });
  fetchTableLineage
    .mockResolvedValueOnce({
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
    })
    .mockResolvedValueOnce({
      table: {
        id: 2,
        key: "table:dm.user_order_summary",
        name: "dm.user_order_summary",
      },
      upstream_tables: [{ id: 1, key: "table:ods.orders", name: "ods.orders" }],
      downstream_tables: [],
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
  expect(await screen.findByText("全量表级总览")).toBeTruthy();
  expect(fetchTableLineage).toHaveBeenCalledWith("table:ods.orders");
  expect(fetchTableLineage).toHaveBeenCalledWith("table:dm.user_order_summary");
});
