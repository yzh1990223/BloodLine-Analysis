package com.example.repository;

public class OrderRepository {
    public void saveSummary() {
        String sql = "insert into dm.user_order_summary select * from ods.orders";
        execute(sql);
    }

    private void execute(String sql) {
        // no-op fixture
    }
}
