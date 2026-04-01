public class FrmsReportService implements ReportPort {
    private final ReportRepository reportRepository = new ReportRepository();

    @Override
    public String loadSummary() {
        return reportRepository.loadSummary();
    }
}
