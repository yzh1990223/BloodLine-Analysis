package com.demo.bridge;

import java.util.List;
import org.apache.ibatis.annotations.Select;

public interface UserMapper {
    @Select("select * from dm.user_info")
    List<UserEntity> list();
}
