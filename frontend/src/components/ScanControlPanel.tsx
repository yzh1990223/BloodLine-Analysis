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
  metadata_databases: string;
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

function toFormState(inputs?: ScanRequestPayload): ScanFormState {
  return {
    repo_path: inputs?.repo_paths?.join(", ") ?? inputs?.repo_path ?? "",
    java_source_root: inputs?.java_source_roots?.join(", ") ?? inputs?.java_source_root ?? "",
    mysql_dsn: inputs?.mysql_dsn ?? "",
    metadata_databases: inputs?.metadata_databases?.join(", ") ?? "",
  };
}

function parseCommaSeparatedPaths(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
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
    metadata_databases: "",
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
        setFormState(toFormState(response.scan_run?.inputs));
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
    const repoPaths = parseCommaSeparatedPaths(formState.repo_path);
    const javaSourceRoots = parseCommaSeparatedPaths(formState.java_source_root);
    const mysqlDsn = formState.mysql_dsn.trim();
    const metadataDatabases = parseCommaSeparatedPaths(formState.metadata_databases);

    if (repoPaths.length > 0) {
      payload.repo_paths = repoPaths;
    }
    if (javaSourceRoots.length > 0) {
      payload.java_source_roots = javaSourceRoots;
    }
    if (mysqlDsn) {
      payload.mysql_dsn = mysqlDsn;
    }
    if (metadataDatabases.length > 0) {
      payload.metadata_databases = metadataDatabases;
    }

    if (!payload.repo_paths && !payload.java_source_roots) {
      setShowAdvanced(true);
      setError("请至少填写 1 个 Repo 文件路径或 1 个 Java 源码目录，多个路径请用英文逗号分隔。");
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setStatusLabel("运行中");

    try {
      await createScan(payload);
      const latest = await fetchLatestScanRun();
      setLatestScanRun(latest.scan_run);
      setFormState(toFormState(latest.scan_run?.inputs));
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
              placeholder="/data/bloodline/merged.repo, /data/bloodline/extra.repo"
            />
            <span className="field-hint">支持填写多个 Repo 文件路径，多个路径请用英文逗号分隔。</span>
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
              placeholder="/data/bloodline/java-src, /data/bloodline/java-extra"
            />
            <span className="field-hint">支持填写多个 Java 源码目录，多个目录请用英文逗号分隔。</span>
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
          <label>
            元数据数据库列表
            <input
              aria-label="元数据数据库列表"
              value={formState.metadata_databases}
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  metadata_databases: event.target.value,
                }))
              }
              placeholder="winddf, frms, dp"
            />
          </label>
        </div>
      ) : null}
    </section>
  );
}
