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
      repo_paths: ["/data/demo.repo", "/data/extra.repo"],
      java_source_roots: ["/data/java", "/data/java-extra"],
    },
  });

  render(<ScanControlPanel onScanCompleted={() => {}} />);

  expect(await screen.findByText("最近扫描状态")).toBeTruthy();
  expect(screen.getByText("已完成")).toBeTruthy();

  fireEvent.click(screen.getByRole("button", { name: "高级配置" }));
  fireEvent.change(screen.getByLabelText("Repo 文件路径"), {
    target: { value: "/data/demo.repo, /data/extra.repo" },
  });
  fireEvent.change(screen.getByLabelText("Java 源码目录"), {
    target: { value: "/data/java, /data/java-extra" },
  });
  fireEvent.change(screen.getByLabelText("元数据数据库列表"), {
    target: { value: "dm, ods" },
  });
  fireEvent.click(screen.getByRole("button", { name: "重新扫描解析" }));

  await waitFor(() => {
    expect(createScan).toHaveBeenCalledWith({
      repo_paths: ["/data/demo.repo", "/data/extra.repo"],
      java_source_roots: ["/data/java", "/data/java-extra"],
      metadata_databases: ["dm", "ods"],
    });
  });
});

test("auto-fills the latest saved scan inputs", async () => {
  fetchLatestScanRun.mockResolvedValue({
    scan_run: {
      id: 15,
      status: "completed",
      started_at: "2026-03-31T01:00:00Z",
      finished_at: "2026-03-31T01:01:00Z",
      created_at: "2026-03-31T01:00:00Z",
      inputs: {
        repo_paths: ["/data/latest.repo", "/data/extra.repo"],
        java_source_roots: ["/data/latest-java", "/data/java-two"],
        mysql_dsn: "mysql+pymysql://user:pass@localhost/dm",
        metadata_databases: ["dm", "ods", "frms"],
      },
    },
  });

  render(<ScanControlPanel onScanCompleted={() => {}} />);

  expect(await screen.findByText("最近扫描状态")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "高级配置" }));

  await waitFor(() => {
    expect((screen.getByLabelText("Repo 文件路径") as HTMLInputElement).value).toBe(
      "/data/latest.repo, /data/extra.repo",
    );
    expect((screen.getByLabelText("Java 源码目录") as HTMLInputElement).value).toBe(
      "/data/latest-java, /data/java-two",
    );
    expect((screen.getByLabelText("MySQL DSN（预留）") as HTMLInputElement).value).toBe(
      "mysql+pymysql://user:pass@localhost/dm",
    );
    expect((screen.getByLabelText("元数据数据库列表") as HTMLInputElement).value).toBe(
      "dm, ods, frms",
    );
  });
});

test("submits metadata databases as a trimmed list and omits blanks", async () => {
  fetchLatestScanRun.mockResolvedValue({
    scan_run: null,
  });
  createScan.mockResolvedValue({
    scan_run_id: 16,
    status: "completed",
    inputs: {
      java_source_root: "/data/latest-java",
      metadata_databases: ["dm", "ods"],
    },
  });

  render(<ScanControlPanel onScanCompleted={() => {}} />);

  fireEvent.click(screen.getByRole("button", { name: "高级配置" }));
  fireEvent.change(screen.getByLabelText("Java 源码目录"), {
    target: { value: "/data/latest-java" },
  });
  fireEvent.change(screen.getByLabelText("元数据数据库列表"), {
    target: { value: " dm , , ods " },
  });
  fireEvent.click(screen.getByRole("button", { name: "重新扫描解析" }));

  await waitFor(() => {
    expect(createScan).toHaveBeenCalledWith({
      java_source_roots: ["/data/latest-java"],
      metadata_databases: ["dm", "ods"],
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
      repo_paths: ["/data/demo.repo"],
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
      repo_paths: ["/data/demo.repo"],
    });
  });
});

test("allows mysql-only scans and only blocks submission when repo, java, and mysql are all empty", async () => {
  fetchLatestScanRun.mockResolvedValue({
    scan_run: null,
  });
  createScan.mockResolvedValue({
    scan_run_id: 17,
    status: "completed",
    inputs: {
      mysql_dsn: "mysql+pymysql://user:pass@localhost/dm",
    },
  });

  render(<ScanControlPanel onScanCompleted={() => {}} />);

  const submitButton = screen.getByRole("button", { name: "重新扫描解析" });
  expect((submitButton as HTMLButtonElement).disabled).toBe(false);

  fireEvent.click(screen.getByRole("button", { name: "高级配置" }));
  fireEvent.change(screen.getByLabelText("MySQL DSN（预留）"), {
    target: { value: "mysql+pymysql://user:pass@localhost/dm" },
  });
  fireEvent.click(submitButton);

  await waitFor(() => {
    expect(createScan).toHaveBeenCalledWith({
      mysql_dsn: "mysql+pymysql://user:pass@localhost/dm",
    });
  });

  createScan.mockClear();
  fireEvent.change(screen.getByLabelText("MySQL DSN（预留）"), {
    target: { value: "" },
  });
  fireEvent.click(submitButton);
  expect(
    await screen.findByText(
      "请至少填写 Repo 文件路径、Java 源码目录或 MySQL DSN 中的 1 项；如需填写多个路径，请用英文逗号分隔。",
    ),
  ).toBeTruthy();
  expect(screen.getByLabelText("Repo 文件路径")).toBeTruthy();
  expect(createScan).not.toHaveBeenCalled();
});
