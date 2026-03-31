public class ReportServiceImpl implements IReportService {
    private final ReportRepository reportRepository = new ReportRepository();

    @Override
    public String loadSummary() {
        return reportRepository.fetchSummary();
    }
}
