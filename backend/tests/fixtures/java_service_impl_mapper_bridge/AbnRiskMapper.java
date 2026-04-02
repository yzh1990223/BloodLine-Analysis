package com.demo.ib;

import java.util.List;
import java.util.Map;
import org.apache.ibatis.annotations.Select;

public interface AbnRiskMapper {
    @Select("select RISK_CLSF from RP_IB_ABN_RISK_MGMT_DTL_D group by RISK_CLSF")
    List<Map<String, String>> getRiskClsfList();
}
