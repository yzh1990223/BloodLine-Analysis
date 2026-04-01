public interface ValueAnnotatedMapper {
    @Select(value = "select * from ods.orders")
    String loadOrders();
}
