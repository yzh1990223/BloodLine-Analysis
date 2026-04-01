package com.demo.service;

import java.util.List;

public class DailyReportAdapter implements IReportService<ReportRow> {
    private final ReportRepository reportRepository;

    public DailyReportAdapter(ReportRepository reportRepository) {
        this.reportRepository = reportRepository;
    }

    @Override
    public List<ReportRow> loadSummary() {
        return reportRepository.loadSummary();
    }
}
