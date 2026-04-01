import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import App from "../App";

const fetchLatestScanFailures = vi.fn();

vi.mock("../api", () => ({
  fetchLatestScanFailures: (...args: unknown[]) => fetchLatestScanFailures(...args),
}));

afterEach(() => {
  cleanup();
});

beforeEach(() => {
  fetchLatestScanFailures.mockReset();
});

test("renders grouped failures and keeps empty groups collapsed", async () => {
  fetchLatestScanFailures.mockResolvedValue({
    scan_run: {
      id: 32,
      status: "completed",
      started_at: "2026-04-01T10:00:00Z",
      finished_at: "2026-04-01T10:05:00Z",
      created_at: "2026-04-01T10:00:00Z",
    },
    summary: {
      scan_run_id: 32,
      failure_count: 3,
      file_count: 2,
      source_counts: { kettle: 0, java: 2, metadata: 1 },
    },
    groups: [
      {
        source_type: "kettle",
        files: [],
      },
      {
        source_type: "java",
        files: [
          {
            file_path: "src/main/java/com/demo/OrderServiceImpl.java",
            failures: [
              {
                id: 1,
                scan_run_id: 32,
                source_type: "java",
                file_path: "src/main/java/com/demo/OrderServiceImpl.java",
                failure_type: "sql_parse_error",
                message: "unsupported SQL fragment",
                object_key: "java_module:OrderServiceImpl",
                sql_snippet: "select * from dm.user_order_summary",
                created_at: "2026-04-01T10:04:00Z",
              },
              {
                id: 2,
                scan_run_id: 32,
                source_type: "java",
                file_path: "src/main/java/com/demo/OrderServiceImpl.java",
                failure_type: "call_target_resolution_failed",
                message: "unresolved receiver",
                object_key: "java_module:OrderServiceImpl",
                sql_snippet: null,
                created_at: "2026-04-01T10:04:01Z",
              },
            ],
          },
        ],
      },
      {
        source_type: "metadata",
        files: [
          {
            file_path: "dm.v_order_summary",
            failures: [
              {
                id: 3,
                scan_run_id: 32,
                source_type: "metadata",
                file_path: "dm.v_order_summary",
                failure_type: "view_definition_parse_error",
                message: "Missing FROM",
                object_key: "view:dm.v_order_summary",
                sql_snippet: "select * from base1",
                created_at: "2026-04-01T10:04:02Z",
              },
            ],
          },
        ],
      },
    ],
  });

  render(
    <MemoryRouter initialEntries={["/scan-failures"]}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "最近一次扫描失败汇总" })).toBeTruthy();
  expect(screen.getByText("失败总数")).toBeTruthy();
  expect(screen.getByText("3")).toBeTruthy();
  expect(screen.getAllByText("Kettle").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Java").length).toBeGreaterThan(0);
  expect(screen.getAllByText("MySQL 元数据").length).toBeGreaterThan(0);
  expect(screen.getByText("src/main/java/com/demo/OrderServiceImpl.java")).toBeTruthy();
  expect(screen.getByText("sql_parse_error")).toBeTruthy();
  expect(screen.getByText("view_definition_parse_error")).toBeTruthy();
  expect(screen.getByText("暂无失败项")).toBeTruthy();
});

test("supports the failure summary route from the app shell", async () => {
  fetchLatestScanFailures.mockResolvedValue({
    scan_run: null,
    summary: {
      scan_run_id: null,
      failure_count: 0,
      file_count: 0,
      source_counts: { kettle: 0, java: 0, metadata: 0 },
    },
    groups: [
      { source_type: "kettle", files: [] },
      { source_type: "java", files: [] },
      { source_type: "metadata", files: [] },
    ],
  });

  render(
    <MemoryRouter initialEntries={["/scan-failures"]}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("navigation", { name: "主导航" })).toBeTruthy();
  expect(screen.getByRole("link", { name: "失败汇总" })).toBeTruthy();
  expect(screen.getByRole("heading", { name: "最近一次扫描失败汇总" })).toBeTruthy();
});
