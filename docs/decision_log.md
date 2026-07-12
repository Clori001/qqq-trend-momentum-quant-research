# Research Decision Log

所有研究参数均在主回测前声明。敏感性分析只用于评估稳健性，不得重定义主策略。任何研究决定在观察回测表现后不得因收益不理想而修改，除非存在独立理由并在本日志中完整记录。

| ID | Status | Approved decision | Rationale / limitation |
|---|---|---|---|
| DEC-001 | Approved | 指定 QQQ Bloomberg CSV 为唯一数据源，保留 2016-07-11 至 2026-07-10 全部 2,514 行 | 不截短样本，不替换外部数据 |
| DEC-002 | Approved | 跳过前 5 行元数据；物理第 6 行为表头；日期严格按 DD/MM/YYYY 解析 | 避免模糊日期推断 |
| DEC-003 | Approved | 绝对日收益超过 10% 仅触发人工复核；没有独立数据损坏证据不得删除 | 阈值不是异常删除规则；两条记录均保留 |
| DEC-004 | Approved | 共同比较期由已配置主策略最长有效暖机期自动推导，不硬编码日期 | 实际推导为 2017-08-01，并记录于报告 |
| DEC-005 | Approved | 保留 `executed_position = raw_signal.shift(1)` 的 close-to-close 记账；RawSignal_t 使用截至 Close_t 的数据，Position_(t+1) 记录在下一行并归属于 Close_t→Close_(t+1) 收益 | 属于 end-of-day / same-close approximation，不是 next-open 或次日收盘成交；可能相对严格 next-open 偏乐观 |
| DEC-006 | Approved | 主交易成本为每单位换手 5 bps；敏感性为 0/5/10 bps；首次从现金入场收费 | 固定简化成本，不代表真实冲击成本 |
| DEC-007 | Approved | 现金收益为 0；主 Sharpe 年化无风险利率为 0% | 为项目范围内的透明固定假设，不代表当期市场利率 |
| DEC-008 | Approved | 主策略参数：MA20/MA60、Momentum252；Momentum126 仅为预声明稳健性 | 敏感性结果不得成为新主策略 |
| DEC-009 | Approved | 年化使用 252 个交易观测；最大回撤包含初始资本峰值 1 | 所有策略使用一致指标口径 |
| DEC-010 | Approved | `PX_LAST` 调整状态未知，所有结果称为 price-return 而非 total return | 防止超出数据证据的陈述 |

截至 Phase 7，没有未解决的研究口径。调试视频与链接属于后续 Phase 8 操作项，不是研究决定。
