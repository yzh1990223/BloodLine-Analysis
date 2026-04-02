package com.example.service.impl;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.example.dto.AssetManagementNetWorthDto;
import com.example.dto.IntervalRiskReturnIndicatorsDto;
import com.example.repository.AssetManagementNetWorthRepository;
import com.example.service.AssetManagementNetWorthService;

import java.util.List;

public class AssetManagementNetWorthServiceImpl implements AssetManagementNetWorthService {
    private final AssetManagementNetWorthRepository assetManagementNetWorthRepository =
        new AssetManagementNetWorthRepository();

    @Override
    public IPage<AssetManagementNetWorthDto> selectAssetManagementNetWorth(
        String startDate,
        String endDate,
        String sjrq,
        String selectType,
        List<String> fundCodeAmdb,
        String sort,
        Integer page,
        Integer pageSize
    ) {
        return assetManagementNetWorthRepository.selectAssetManagementNetWorth();
    }

    @Override
    public Page<IntervalRiskReturnIndicatorsDto> calculate(
        String startDate,
        String endDate,
        List<String> fundCodeAmdb,
        Double oneYearFixedDepositBenchmarkInterestRateAverage,
        Integer page,
        Integer pageSize
    ) {
        return assetManagementNetWorthRepository.calculate();
    }
}
