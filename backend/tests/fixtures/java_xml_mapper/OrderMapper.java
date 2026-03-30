package com.example.mapper;

public interface OrderMapper {
    java.util.List<String> loadOrders();

    void saveSummary();
}
