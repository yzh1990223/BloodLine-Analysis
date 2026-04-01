import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/unique-report")
public class UniqueReportController {
    private final ReportPort reportService;

    public UniqueReportController(ReportPort reportService) {
        this.reportService = reportService;
    }

    @GetMapping("/summary")
    public String summary() {
        return reportService.loadSummary();
    }
}
