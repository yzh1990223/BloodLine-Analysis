package com.example.service;

public class OrderService {
    public void syncOrderSummary() {
        String query = "select * from ods.orders";
        execute(query);
        orderRepository.saveSummary();
    }

    private void execute(String sql) {
        // no-op fixture
    }
}
