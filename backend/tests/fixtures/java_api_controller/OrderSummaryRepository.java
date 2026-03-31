public class OrderSummaryRepository {
    public String fetchSummary(String orderId) {
        String sql = "select * from dm.user_order_summary where order_id = ?";
        return sql;
    }

    public void saveSummary() {
        String sql = "insert into dm.user_order_summary select * from ods.orders";
    }
}
