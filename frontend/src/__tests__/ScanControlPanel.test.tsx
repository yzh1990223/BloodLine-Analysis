import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { ScanControlPanel } from "../components/ScanControlPanel";

const createScan = vi.fn();
const fetchLatestScanRun = vi.fn();

vi.mock("../api", () => ({
  createScan: (...args: unknown[]) => createScan(...args),
  fetchLatestScanRun: (...args: unknown[]) => fetchLatestScanRun(...args),
}));

beforeEach(() => {
  createScan.mockReset();
  fetchLatestScanRun.mockReset();
});

afterEach(() => {
  cleanup();
});

test("shows latest scan status and lets the user trigger a new scan", async () => {
  fetchLatestScanRun.mockResolvedValue({
    scan_run: {
      id: 12,
      status: "completed",
      started_at: "2026-03-28T01:00:00Z",
      finished_at: "2026-03-28T01:01:00Z",
      created_at: "2026-03-28T01:00:00Z",
    },
  });
  createScan.mockResolvedValue({
    scan_run_id: 13,
    status: "completed",
    inputs: {
      repo_path: "/data/demo.repo",
      java_source_root: "/data/java",
    },
  });

  render(<ScanControlPanel onScanCompleted={() => {}} />);

  expect(await screen.findByText("最近扫描状态")).toBeTruthy();
  expect(screen.getByText("已完成")).toBeTruthy();

  fireEvent.click(screen.getByRole("button", { name: "高级配置" }));
  fireEvent.change(screen.getByLabelText("Repo 文件路径"), {
    target: { value: "/data/demo.repo" },
  });
  fireEvent.change(screen.getByLabelText("Java 源码目录"), {
    target: { value: "/data/java" },
  });
  fireEvent.click(screen.getByRole("button", { name: "重新扫描解析" }));

  await waitFor(() => {
    expect(createScan).toHaveBeenCalledWith({
      repo_path: "/data/demo.repo",
      java_source_root: "/data/java",
    });
  });
});

test("submits a scan when only one path is provided and omits empty fields", async () => {
  fetchLatestScanRun.mockResolvedValue({
    scan_run: null,
  });
  createScan.mockResolvedValue({
    scan_run_id: 14,
    status: "completed",
    inputs: {
      repo_path: "/data/demo.repo",
    },
  });

  render(<ScanControlPanel onScanCompleted={() => {}} />);

  fireEvent.click(screen.getByRole("button", { name: "高级配置" }));
  fireEvent.change(screen.getByLabelText("Repo 文件路径"), {
    target: { value: "/data/demo.repo" },
  });
  fireEvent.click(screen.getByRole("button", { name: "重新扫描解析" }));

  await waitFor(() => {
    expect(createScan).toHaveBeenCalledWith({
      repo_path: "/data/demo.repo",
    });
  });
});

test("keeps the scan button clickable and only blocks submission when both paths are empty", async () => {
  fetchLatestScanRun.mockResolvedValue({
    scan_run: null,
  });

  render(<ScanControlPanel onScanCompleted={() => {}} />);

  const submitButton = screen.getByRole("button", { name: "重新扫描解析" });
  expect((submitButton as HTMLButtonElement).disabled).toBe(false);

  fireEvent.click(submitButton);

  expect(await screen.findByText("请至少填写 Repo 文件路径或 Java 源码目录。")).toBeTruthy();
  expect(screen.getByLabelText("Repo 文件路径")).toBeTruthy();
  expect(createScan).not.toHaveBeenCalled();
});
