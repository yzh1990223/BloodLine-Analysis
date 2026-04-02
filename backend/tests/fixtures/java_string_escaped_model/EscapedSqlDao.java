public class EscapedSqlDao {
    public String loadOrders() {
        String query = "select *\\nfrom ods.orders\\nwhere id = 1";
        return query;
    }
}
