package com.demo.api;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/indirect-report")
public class IndirectReportController {
    private final IReportService reportService;

    public IndirectReportController(IReportService reportService) {
        this.reportService = reportService;
    }

    @GetMapping("/summary")
    public String summary() {
        return reportService.loadSummary();
    }
}
