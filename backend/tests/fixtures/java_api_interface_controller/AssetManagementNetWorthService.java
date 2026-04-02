package com.example.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.example.dto.AssetManagementNetWorthDto;
import com.example.dto.IntervalRiskReturnIndicatorsDto;

import java.util.List;

public interface AssetManagementNetWorthService {
    IPage<AssetManagementNetWorthDto> selectAssetManagementNetWorth(
        String startDate,
        String endDate,
        String sjrq,
        String selectType,
        List<String> fundCodeAmdb,
        String sort,
        Integer page,
        Integer pageSize
    );

    Page<IntervalRiskReturnIndicatorsDto> calculate(
        String startDate,
        String endDate,
        List<String> fundCodeAmdb,
        Double oneYearFixedDepositBenchmarkInterestRateAverage,
        Integer page,
        Integer pageSize
    );
}
