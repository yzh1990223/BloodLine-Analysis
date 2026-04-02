package com.demo.api;

public class ReportServiceImpl extends AbstractReportService {
    private final ReportRepository reportRepository = new ReportRepository();

    @Override
    public String loadSummary() {
        return reportRepository.fetchSummary();
    }
}
