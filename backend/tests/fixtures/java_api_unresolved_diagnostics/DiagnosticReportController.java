package com.demo.diag;

import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/diagnostic-report")
public class DiagnosticReportController {
    private final IReportService reportService;
    private final AuditService auditService;

    public DiagnosticReportController(IReportService reportService, AuditService auditService) {
        this.reportService = reportService;
        this.auditService = auditService;
    }

    @GetMapping("/summary")
    public List<ReportRow> summary() {
        auditService.audit();
        return reportService.loadSummary();
    }
}
