package com.demo.api;

import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/bound-report")
public class BoundReportController {
    private final IReportService<ReportRow> reportService;

    public BoundReportController(IReportService<ReportRow> reportService) {
        this.reportService = reportService;
    }

    @GetMapping("/summary")
    public List<ReportRow> summary() {
        return reportService.loadSummary();
    }
}
