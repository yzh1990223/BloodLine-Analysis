public interface EscapedAnnotatedMapper {
    @Select(
        "select *\\n" +
        "from ods.orders\\n" +
        "where id = #{id}"
    )
    String loadOrders();
}
