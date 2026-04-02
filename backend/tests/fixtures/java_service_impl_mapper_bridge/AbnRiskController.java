package com.demo.ib;

import java.util.List;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/IbApp/IbAbn")
public class AbnRiskController {
    private final IAbnRiskService abnRiskService;

    public AbnRiskController(IAbnRiskService abnRiskService) {
        this.abnRiskService = abnRiskService;
    }

    @GetMapping("/getRiskClsfList")
    public List<Map<String, String>> getRiskClsfList() {
        return abnRiskService.getRiskClsfList();
    }
}
