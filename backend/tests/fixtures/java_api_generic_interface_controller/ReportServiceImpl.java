public class ReportServiceImpl implements IReportService<ReportRow> {
    private final ReportRepository reportRepository = new ReportRepository();

    @Override
    public String loadSummary() {
        return reportRepository.fetchSummary();
    }
}
