import { useEffect, useState } from "react";
import { createScan, fetchLatestScanRun } from "../api";
import { LatestScanRunResponse, ScanRequestPayload, ScanRunSummary } from "../types";

interface ScanControlPanelProps {
  onScanCompleted: () => Promise<void> | void;
}

interface ScanFormState {
  repo_path: string;
  java_source_root: string;
  mysql_dsn: string;
}

function formatStatus(status: string | null) {
  if (status === "running") {
    return "运行中";
  }
  if (status === "completed") {
    return "已完成";
  }
  if (status === "failed") {
    return "失败";
  }
  return "未开始";
}

function latestTime(scanRun: ScanRunSummary | null) {
  if (!scanRun?.finished_at && !scanRun?.started_at && !scanRun?.created_at) {
    return "暂无记录";
  }
  return scanRun.finished_at ?? scanRun.started_at ?? scanRun.created_at ?? "暂无记录";
}

export function ScanControlPanel({ onScanCompleted }: ScanControlPanelProps) {
  const [latestScanRun, setLatestScanRun] = useState<LatestScanRunResponse["scan_run"]>(null);
  const [statusLabel, setStatusLabel] = useState("未开始");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [formState, setFormState] = useState<ScanFormState>({
    repo_path: "",
    java_source_root: "",
    mysql_dsn: "",
  });

  useEffect(() => {
    let active = true;

    async function loadLatestScanRun() {
      try {
        const response = await fetchLatestScanRun();
        if (!active) {
          return;
        }
        setLatestScanRun(response.scan_run);
        setStatusLabel(formatStatus(response.scan_run?.status ?? null));
      } catch (err) {
        if (!active) {
          return;
        }
        setError(err instanceof Error ? err.message : "加载扫描状态失败");
      }
    }

    void loadLatestScanRun();
    return () => {
      active = false;
    };
  }, []);

  async function handleSubmit() {
    const payload: ScanRequestPayload = {};
    const repoPath = formState.repo_path.trim();
    const javaSourceRoot = formState.java_source_root.trim();
    const mysqlDsn = formState.mysql_dsn.trim();

    if (repoPath) {
      payload.repo_path = repoPath;
    }
    if (javaSourceRoot) {
      payload.java_source_root = javaSourceRoot;
    }
    if (mysqlDsn) {
      payload.mysql_dsn = mysqlDsn;
    }

    if (!payload.repo_path && !payload.java_source_root) {
      setShowAdvanced(true);
      setError("请至少填写 Repo 文件路径或 Java 源码目录。");
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setStatusLabel("运行中");

    try {
      await createScan(payload);
      const latest = await fetchLatestScanRun();
      setLatestScanRun(latest.scan_run);
      setStatusLabel(formatStatus(latest.scan_run?.status ?? "completed"));
      await onScanCompleted();
    } catch (err) {
      setStatusLabel("失败");
      setError(err instanceof Error ? err.message : "触发扫描失败");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="panel scan-panel">
      <div className="panel-header">
        <div>
          <h2>扫描控制面板</h2>
          <p className="panel-subtitle">手动触发一次重新扫描，并查看最近一次解析状态。</p>
        </div>
        <div className={`scan-status scan-status-${statusLabel}`}>
          <span className="scan-status-label">最近扫描状态</span>
          <strong>{statusLabel}</strong>
        </div>
      </div>

      <div className="scan-meta">
        <span>最近更新时间：{latestTime(latestScanRun)}</span>
        {latestScanRun?.id ? <span>扫描记录 ID：{latestScanRun.id}</span> : null}
      </div>

      <div className="scan-actions">
        <button
          type="button"
          className="primary-action"
          onClick={() => void handleSubmit()}
          disabled={isSubmitting}
        >
          {isSubmitting ? "扫描进行中..." : "重新扫描解析"}
        </button>
        <button
          type="button"
          className="secondary-action"
          onClick={() => setShowAdvanced((current) => !current)}
        >
          {showAdvanced ? "收起高级配置" : "高级配置"}
        </button>
      </div>

      {error ? <p className="error">{error}</p> : null}

      {showAdvanced ? (
        <div className="scan-form">
          <label>
            Repo 文件路径
            <input
              aria-label="Repo 文件路径"
              value={formState.repo_path}
              onChange={(event) =>
                setFormState((current) => ({ ...current, repo_path: event.target.value }))
              }
              placeholder="/data/bloodline/merged.repo"
            />
          </label>
          <label>
            Java 源码目录
            <input
              aria-label="Java 源码目录"
              value={formState.java_source_root}
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  java_source_root: event.target.value,
                }))
              }
              placeholder="/data/bloodline/java-src"
            />
          </label>
          <label>
            MySQL DSN（预留）
            <input
              aria-label="MySQL DSN（预留）"
              value={formState.mysql_dsn}
              onChange={(event) =>
                setFormState((current) => ({ ...current, mysql_dsn: event.target.value }))
              }
              placeholder="mysql+pymysql://user:password@host:3306/db"
            />
          </label>
        </div>
      ) : null}
    </section>
  );
}
