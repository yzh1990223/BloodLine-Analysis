package com.example.mapper;

public interface AnnotatedMapper {
    @Select("select * from ods.orders")
    java.util.List<String> loadOrders();

    @Insert("insert into dm.user_order_summary select * from ods.orders")
    void saveSummary();
}
