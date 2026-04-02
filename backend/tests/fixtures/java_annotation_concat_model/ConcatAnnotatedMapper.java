public interface ConcatAnnotatedMapper {
    @Select(
        "select * " +
        "from ods.orders"
    )
    String loadOrders();

    @Insert(
        value = "insert into dm.user_order_summary " +
        "select * from ods.orders"
    )
    int saveSummary();
}
