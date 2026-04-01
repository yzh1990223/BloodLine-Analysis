package com.demo.diag;

import java.util.List;

public class ReportRepository {
    public List<ReportRow> loadSummary() {
        String sql = "select * from dm.user_order_summary";
        return List.of();
    }
}
