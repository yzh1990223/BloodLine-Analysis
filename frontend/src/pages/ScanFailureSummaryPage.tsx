import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchLatestScanFailures } from "../api";
import { ScanFailureSummaryResponse, ScanFailureSourceGroup } from "../types";

const SOURCE_LABELS: Record<string, string> = {
  kettle: "Kettle",
  java: "Java",
  metadata: "MySQL 元数据",
};

function sourceLabel(sourceType: string): string {
  return SOURCE_LABELS[sourceType] ?? sourceType;
}

function latestTime(scanRun: ScanFailureSummaryResponse["scan_run"]) {
  return scanRun?.finished_at ?? scanRun?.started_at ?? scanRun?.created_at ?? "暂无记录";
}

function sourceFailureCount(group: ScanFailureSourceGroup) {
  return group.files.reduce((total, fileGroup) => total + fileGroup.failures.length, 0);
}

export function ScanFailureSummaryPage() {
  const [payload, setPayload] = useState<ScanFailureSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const signal = { cancelled: false };

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const response = await fetchLatestScanFailures();
        if (!signal.cancelled) {
          setPayload(response);
        }
      } catch (err) {
        if (!signal.cancelled) {
          setError(err instanceof Error ? err.message : "加载扫描失败汇总失败");
          setPayload(null);
        }
      } finally {
        if (!signal.cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      signal.cancelled = true;
    };
  }, []);

  const summaryCards = useMemo(() => {
    if (!payload) {
      return [];
    }

    return [
      { label: "失败总数", value: payload.summary.failure_count },
      { label: "失败文件数", value: payload.summary.file_count },
      { label: "Kettle", value: payload.summary.source_counts.kettle ?? 0 },
      { label: "Java", value: payload.summary.source_counts.java ?? 0 },
      { label: "MySQL 元数据", value: payload.summary.source_counts.metadata ?? 0 },
    ];
  }, [payload]);

  return (
    <main className="page">
      <header className="page-header">
        <p className="eyebrow">BloodLine Analysis</p>
        <h1>最近一次扫描失败汇总</h1>
        <p className="subtitle">
          按 Kettle、Java 和 MySQL 元数据分组，聚合展示最近一次扫描里最容易排查的失败项。
        </p>
        <div className="page-actions">
          <Link to="/">返回总览</Link>
          <Link to="/analysis/cycles">闭环分析</Link>
        </div>
      </header>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>扫描概览</h2>
            <p className="panel-subtitle">仅展示最近一次扫描的失败结果，方便快速定位局部问题。</p>
          </div>
        </div>

        {loading ? <p>失败汇总加载中...</p> : null}
        {error ? <p className="error">{error}</p> : null}
        {!loading && !error && payload ? (
          <div className="overview-stats">
            {summaryCards.map((card) => (
              <div key={card.label} className="overview-stat-card">
                <span>{card.label}</span>
                <strong>{card.value}</strong>
              </div>
            ))}
            <div className="overview-stat-card">
              <span>最近扫描 ID</span>
              <strong>{payload.scan_run?.id ?? "暂无"}</strong>
            </div>
          </div>
        ) : null}
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>分组明细</h2>
            <p className="panel-subtitle">
              失败项按来源类型分组，并在文件级聚合后展开每条具体失败原因。
            </p>
          </div>
          {payload ? <span className="scan-meta-inline">最近更新时间：{latestTime(payload.scan_run)}</span> : null}
        </div>

        {!loading && !error && payload ? (
          <div className="failure-summary-list">
            {payload.groups.every((group) => sourceFailureCount(group) === 0) ? (
              <p className="failure-empty">最近一次扫描没有记录到失败项。</p>
            ) : null}
            {payload.groups.map((group) => {
              const failureCount = sourceFailureCount(group);
              const hasFailures = failureCount > 0;
              return (
                <details key={group.source_type} className="failure-source-group" open={hasFailures}>
                  <summary className="failure-source-summary">
                    <span>{sourceLabel(group.source_type)}</span>
                    <span>{hasFailures ? `${group.files.length} 个文件 · ${failureCount} 条失败` : "暂无失败项"}</span>
                  </summary>
                  {hasFailures ? (
                    <div className="failure-file-list">
                      {group.files.map((fileGroup) => (
                        <details key={fileGroup.file_path} className="failure-file-group" open>
                          <summary className="failure-file-summary">
                            <span>{fileGroup.file_path}</span>
                            <span>{`${fileGroup.failures.length} 条失败`}</span>
                          </summary>
                          <ul className="failure-item-list">
                            {fileGroup.failures.map((failure) => (
                              <li key={failure.id} className="failure-item">
                                <div className="failure-item-header">
                                  <strong>{failure.failure_type}</strong>
                                  {failure.object_key ? <span>{failure.object_key}</span> : null}
                                </div>
                                <p className="failure-message">{failure.message}</p>
                                {failure.sql_snippet ? (
                                  <pre className="failure-snippet">{failure.sql_snippet}</pre>
                                ) : null}
                              </li>
                            ))}
                          </ul>
                        </details>
                      ))}
                    </div>
                  ) : (
                    <p className="failure-empty">该来源当前没有失败项。</p>
                  )}
                </details>
              );
            })}
          </div>
        ) : null}
      </section>
    </main>
  );
}
