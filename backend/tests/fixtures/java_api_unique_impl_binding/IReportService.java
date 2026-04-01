package com.demo.api;

import java.util.List;

public interface IReportService<T> {
    List<T> loadSummary();
}
