package com.example.service;

public class OrderService {
    public void syncOrderSummary() {
        orderRepository.saveSummary();
    }
}
