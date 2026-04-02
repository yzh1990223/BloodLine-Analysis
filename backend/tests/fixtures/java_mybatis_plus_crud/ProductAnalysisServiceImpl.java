package com.demo.mybatispluscrud;

public class ProductAnalysisServiceImpl extends ServiceImpl<RpAmFundRiskprofitMapper, RpAmFundRiskprofitEntity>
    implements ProductAnalysisService {
    @Override
    public Page<RpAmFundRiskprofitEntity> selectAMProductNetWorthAnalysis() {
        return getBaseMapper().selectPage(new Page<>(), new LambdaQueryWrapper<>());
    }
}
