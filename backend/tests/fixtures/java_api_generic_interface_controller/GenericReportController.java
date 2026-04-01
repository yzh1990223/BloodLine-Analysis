import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/generic-report")
public class GenericReportController {
    private final IReportService<ReportRow> reportService;

    public GenericReportController(IReportService<ReportRow> reportService) {
        this.reportService = reportService;
    }

    @GetMapping("/summary")
    public String summary() {
        return reportService.loadSummary();
    }
}
