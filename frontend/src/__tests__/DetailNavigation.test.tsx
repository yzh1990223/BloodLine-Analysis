import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";
import { ImpactPage } from "../pages/ImpactPage";
import { TableDetailPage } from "../pages/TableDetailPage";

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

vi.stubGlobal("ResizeObserver", ResizeObserverMock);

afterEach(() => {
  cleanup();
});

vi.mock("../api", () => ({
  fetchConnectedLineage: () =>
    Promise.resolve({
      table_lineage: {
        table: { id: 1, key: "table:ods.orders", name: "ods.orders" },
        upstream_tables: [],
        downstream_tables: [],
        related_objects: { jobs: [], java_modules: [], transformations: [] },
      },
      items: [
        {
          table: { id: 1, key: "table:ods.orders", name: "ods.orders" },
          upstream_tables: [],
          downstream_tables: [],
          related_objects: { jobs: [], java_modules: [], transformations: [] },
        },
      ],
    }),
  fetchTableImpact: () =>
    Promise.resolve({
      table: { id: 1, key: "table:ods.orders", name: "ods.orders" },
      upstream_tables: [],
      downstream_tables: [],
      impacted_tables: [],
      related_objects: { jobs: [], java_modules: [], transformations: [] },
    }),
}));

test("table detail page shows a back button to the overview", async () => {
  render(
    <MemoryRouter initialEntries={["/tables/table%3Aods.orders"]}>
      <Routes>
        <Route path="/tables/:tableKey" element={<TableDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );

  expect(await screen.findByRole("link", { name: "返回总览" })).toBeTruthy();
});

test("impact page shows back buttons to detail and overview", async () => {
  render(
    <MemoryRouter initialEntries={["/tables/table%3Aods.orders/impact"]}>
      <Routes>
        <Route path="/tables/:tableKey/impact" element={<ImpactPage />} />
      </Routes>
    </MemoryRouter>,
  );

  expect(await screen.findByRole("link", { name: "返回表详情" })).toBeTruthy();
  expect(screen.getAllByRole("link", { name: "返回总览" }).length).toBeGreaterThan(0);
});
