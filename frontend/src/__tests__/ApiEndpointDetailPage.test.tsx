import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";
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
          id: 11,
          key: "api:GET /users",
          name: "GET /users",
          object_type: "api_endpoint",
          payload: {
            object_type: "api_endpoint",
            http_method: "GET",
            route: "/users",
            diagnostics: {
              resolved_calls: 1,
              unresolved_calls: 1,
              unresolved_reasons: [
                { call: "auditService.audit", reason: "unresolved_target_method" },
              ],
              read_table_count: 1,
              write_table_count: 0,
            },
          },
        },
        upstream_tables: [],
        downstream_tables: [
          { id: 21, key: "table:dm.user_info", name: "dm.user_info", object_type: "data_table" },
        ],
        related_objects: { jobs: [], java_modules: [], api_endpoints: [], transformations: [] },
      },
      items: [
        {
          table: {
            id: 11,
            key: "api:GET /users",
            name: "GET /users",
            object_type: "api_endpoint",
            payload: {
              object_type: "api_endpoint",
              http_method: "GET",
              route: "/users",
              diagnostics: {
                resolved_calls: 1,
                unresolved_calls: 1,
                unresolved_reasons: [
                  { call: "auditService.audit", reason: "unresolved_target_method" },
                ],
                read_table_count: 1,
                write_table_count: 0,
              },
            },
          },
          upstream_tables: [],
          downstream_tables: [
            { id: 21, key: "table:dm.user_info", name: "dm.user_info", object_type: "data_table" },
          ],
          related_objects: { jobs: [], java_modules: [], api_endpoints: [], transformations: [] },
        },
      ],
    }),
}));

test("api endpoint detail page renders diagnostics panel", async () => {
  render(
    <MemoryRouter initialEntries={["/tables/api%3AGET%20%2Fusers"]}>
      <Routes>
        <Route path="/tables/:tableKey" element={<TableDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "GET /users" })).toBeTruthy();
  expect(screen.getByRole("heading", { name: "API 诊断" })).toBeTruthy();
  expect(screen.getByText("已解析调用：1")).toBeTruthy();
  expect(screen.getByText("未解析调用：1")).toBeTruthy();
  expect(screen.getByText("读表数：1")).toBeTruthy();
  expect(screen.getByText("写表数：0")).toBeTruthy();
  expect(screen.getByText("auditService.audit")).toBeTruthy();
  expect(screen.getByText("unresolved_target_method")).toBeTruthy();
});
