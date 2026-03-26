package com.example.dao;

public class UserOrderDao {
    public void loadOrders() {
        String sql = "select * from ods.orders";
        execute(sql);
    }

    public void buildSummary() {
        String sql = "insert into dm.user_order_summary select * from ods.orders";
        execute(sql);
    }

    private void execute(String sql) {
        // no-op fixture
    }
}
