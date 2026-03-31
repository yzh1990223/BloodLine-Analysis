public class OrderSummaryService {
    private final OrderSummaryRepository orderSummaryRepository = new OrderSummaryRepository();

    public String loadSummary(String orderId) {
        return orderSummaryRepository.fetchSummary(orderId);
    }

    public void refreshSummary() {
        orderSummaryRepository.saveSummary();
    }
}
