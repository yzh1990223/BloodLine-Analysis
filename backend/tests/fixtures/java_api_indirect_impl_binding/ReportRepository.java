package com.demo.api;

public class ReportRepository {
    public String fetchSummary() {
        String query = "select * from dm.user_order_summary";
        return query;
    }
}
