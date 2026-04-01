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
        table: {
          id: 1,
          key: "table:ods.orders",
          name: "ods.orders",
          display_name: "订单表",
            metadata: {
              database_name: "ods",
              object_name: "orders",
              object_kind: "view",
              comment: "订单表",
              column_count: 8,
              metadata_source: "mysql_information_schema",
            view_parse_status: "failed",
            view_parse_error: "Missing )",
            view_definition: "select * from ods.orders where id in (",
          },
        },
        upstream_tables: [],
        downstream_tables: [],
        related_objects: { jobs: [], java_modules: [], transformations: [] },
      },
      items: [
        {
          table: { id: 1, key: "table:ods.orders", name: "ods.orders", display_name: "订单表" },
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

test("table detail page renders metadata summary when available", async () => {
  render(
    <MemoryRouter initialEntries={["/tables/table%3Aods.orders"]}>
      <Routes>
        <Route path="/tables/:tableKey" element={<TableDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "订单表" })).toBeTruthy();
  expect(screen.getAllByText("ods.orders").length).toBeGreaterThan(0);
  expect(screen.getByText("数据库：ods")).toBeTruthy();
  expect(screen.getByText("技术名称：orders")).toBeTruthy();
  expect(screen.getByText("对象种类：view")).toBeTruthy();
  expect(screen.getByText("字段数：8")).toBeTruthy();
  expect(screen.getByText("中文名称：订单表")).toBeTruthy();
  expect(screen.getByText("视图解析状态：失败")).toBeTruthy();
  expect(screen.getByText("失败原因：Missing )")).toBeTruthy();
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
