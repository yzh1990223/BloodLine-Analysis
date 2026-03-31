import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/orders")
public class OrderSummaryController {
    private final OrderSummaryService orderSummaryService = new OrderSummaryService();

    @GetMapping("/{id}")
    public String getSummary(@PathVariable String id) {
        return orderSummaryService.loadSummary(id);
    }

    @PostMapping("/summary")
    public void refreshSummary() {
        orderSummaryService.refreshSummary();
    }
}
