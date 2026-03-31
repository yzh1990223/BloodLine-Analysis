package com.example.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.example.dto.AssetManagementNetWorthDto;
import com.example.dto.IntervalRiskReturnIndicatorsDto;
import com.example.service.AssetManagementNetWorthService;
import com.example.web.Result;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/assetManagement")
public class AssetManagementNetWorthController {

    private AssetManagementNetWorthService amNetWorthService;

    @GetMapping("/selectAssetManagementNetWorth")
    public Result<IPage<AssetManagementNetWorthDto>> selectAssetManagementNetWorth(
        @RequestParam(value = "startDate", required = false) String startDate,
        @RequestParam(value = "endDate", required = false) String endDate,
        @RequestParam(value = "sjrq", required = false) String sjrq,
        @RequestParam("selectType") String selectType,
        @RequestParam(value = "fundCodeAmdb", required = false) List<String> fundCodeAmdb,
        @RequestParam(value = "sort", required = false) String sort,
        @RequestParam("page") Integer page,
        @RequestParam(value = "pageSize", defaultValue = "10") Integer pageSize
    ) {
        IPage<AssetManagementNetWorthDto> data = amNetWorthService.selectAssetManagementNetWorth(
            startDate,
            endDate,
            sjrq,
            selectType,
            fundCodeAmdb,
            sort,
            page,
            pageSize
        );
        return Result.data(data);
    }

    @GetMapping("/calculate")
    public Result<Page<IntervalRiskReturnIndicatorsDto>> calculate(
        @RequestParam("startDate") String startDate,
        @RequestParam("endDate") String endDate,
        @RequestParam(value = "fundCodeAmdb", required = false) List<String> fundCodeAmdb,
        @RequestParam(value = "oneYearFixedDepositBenchmarkInterestRateAverage") Double oneYearFixedDepositBenchmarkInterestRateAverage,
        @RequestParam("page") Integer page,
        @RequestParam(value = "pageSize", defaultValue = "10") Integer pageSize
    ) {
        Page<IntervalRiskReturnIndicatorsDto> data = amNetWorthService.calculate(
            startDate,
            endDate,
            fundCodeAmdb,
            oneYearFixedDepositBenchmarkInterestRateAverage,
            page,
            pageSize
        );
        return Result.data(data);
    }
}
