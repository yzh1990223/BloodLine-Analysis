package com.demo.mybatispluscrud;

import java.util.List;

public interface BaseMapper<T> {
    Page<T> selectPage(Page<T> page, LambdaQueryWrapper<T> queryWrapper);

    List<T> selectList(LambdaQueryWrapper<T> queryWrapper);
}
