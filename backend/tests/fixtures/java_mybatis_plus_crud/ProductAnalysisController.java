package com.demo.mybatispluscrud;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/assetManagement")
public class ProductAnalysisController {
    private final ProductAnalysisService productAnalysisService;
    private final ProductAnalysisTidbService productAnalysisTidbService;

    public ProductAnalysisController(
        ProductAnalysisService productAnalysisService,
        ProductAnalysisTidbService productAnalysisTidbService
    ) {
        this.productAnalysisService = productAnalysisService;
        this.productAnalysisTidbService = productAnalysisTidbService;
    }

    @GetMapping("/selectAMProductNetWorthAnalysis")
    public Page<RpAmFundRiskprofitEntity> selectAMProductNetWorthAnalysis() {
        Page<RpAmFundRiskprofitEntity> productAnalysis = productAnalysisService.selectAMProductNetWorthAnalysis();
        productAnalysisTidbService.selectAMProductNetWorthAnalysis();
        return productAnalysis;
    }
}
