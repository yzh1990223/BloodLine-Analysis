import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, test } from "vitest";
import App from "../App";

afterEach(() => {
  cleanup();
});

test("renders the global navigation on the home route", () => {
  render(
    <MemoryRouter initialEntries={["/"]}>
      <App />
    </MemoryRouter>,
  );

  expect(screen.getByRole("navigation", { name: "主导航" })).toBeTruthy();
  expect(screen.getAllByRole("link", { name: "总览" }).length).toBeGreaterThan(0);
  expect(screen.getByRole("link", { name: "表搜索" })).toBeTruthy();
  expect(screen.getByRole("link", { name: "失败汇总" })).toBeTruthy();
  expect(screen.getByText("当前位置")).toBeTruthy();
});

test("renders breadcrumb location on the table detail route", () => {
  render(
    <MemoryRouter initialEntries={["/tables/table%3Aods.orders"]}>
      <App />
    </MemoryRouter>,
  );

  const breadcrumbs = screen.getByLabelText("面包屑");
  expect(within(breadcrumbs).getByText("当前位置")).toBeTruthy();
  expect(within(breadcrumbs).getByRole("link", { name: "总览" })).toBeTruthy();
  expect(within(breadcrumbs).getByText("表详情")).toBeTruthy();
  expect(within(breadcrumbs).getByText("ods.orders")).toBeTruthy();
});

test("renders breadcrumb location on the object list route", () => {
  render(
    <MemoryRouter initialEntries={["/objects?type=source_table"]}>
      <App />
    </MemoryRouter>,
  );

  const breadcrumbs = screen.getByLabelText("面包屑");
  expect(within(breadcrumbs).getByRole("link", { name: "总览" })).toBeTruthy();
  expect(within(breadcrumbs).getByText("对象列表")).toBeTruthy();
});

test("renders breadcrumb location on the failure summary route", () => {
  render(
    <MemoryRouter initialEntries={["/scan-failures"]}>
      <App />
    </MemoryRouter>,
  );

  const breadcrumbs = screen.getByLabelText("面包屑");
  expect(within(breadcrumbs).getByRole("link", { name: "总览" })).toBeTruthy();
  expect(within(breadcrumbs).getByText("失败汇总")).toBeTruthy();
});
