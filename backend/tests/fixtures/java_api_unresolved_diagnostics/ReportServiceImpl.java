package com.demo.diag;

import java.util.List;

public class ReportServiceImpl implements IReportService {
    private final ReportRepository reportRepository;

    public ReportServiceImpl(ReportRepository reportRepository) {
        this.reportRepository = reportRepository;
    }

    @Override
    public List<ReportRow> loadSummary() {
        return reportRepository.loadSummary();
    }
}
