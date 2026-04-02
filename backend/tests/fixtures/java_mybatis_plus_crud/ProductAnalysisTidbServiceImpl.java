package com.demo.mybatispluscrud;

public class ProductAnalysisTidbServiceImpl
    extends ServiceImpl<RpAmFundRiskprofitTidbMapper, RpAmFundRiskprofitTidbEntity>
    implements ProductAnalysisTidbService {
    @Override
    public Page<RpAmFundRiskprofitTidbEntity> selectAMProductNetWorthAnalysis() {
        return getBaseMapper().selectPage(new Page<>(), new LambdaQueryWrapper<>());
    }
}
