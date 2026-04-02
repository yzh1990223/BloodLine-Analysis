package com.example.repository;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.example.dto.AssetManagementNetWorthDto;
import com.example.dto.IntervalRiskReturnIndicatorsDto;

public class AssetManagementNetWorthRepository {
    public IPage<AssetManagementNetWorthDto> selectAssetManagementNetWorth() {
        String query = "select * from dp.dm_am_prod_daily_idx_tab_d";
        return null;
    }

    public Page<IntervalRiskReturnIndicatorsDto> calculate() {
        String query = "select * from dp.dm_am_prod_daily_idx_tab_d";
        return null;
    }
}
