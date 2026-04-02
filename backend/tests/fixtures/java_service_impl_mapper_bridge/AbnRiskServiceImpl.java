package com.demo.ib;

import java.util.List;
import java.util.Map;

public class AbnRiskServiceImpl extends ServiceImpl<AbnRiskMapper, AbnRiskEntity> implements IAbnRiskService {
    @Override
    public List<Map<String, String>> getRiskClsfList() {
        return getBaseMapper().getRiskClsfList();
    }
}
