# Debugging and Demonstration Guide

建议在 VS Code 中打开项目根目录，并选择 `ccb_quant` 环境解释器。

## 推荐断点

1. `src/ccb_quant/data.py`：日期解析、字段映射和异常收益复核列表。
2. `src/ccb_quant/indicators.py`：MA60 与 Momentum252 首个有效值。
3. `src/ccb_quant/signals.py`：月末 decision flag 和 forward-hold。
4. `src/ccb_quant/backtest.py`：`executed = raw_signal.shift(1)`、turnover、cost 和 net return。
5. `src/ccb_quant/metrics.py`：running peak、drawdown 和 annualization。

## Watches

`raw_signal`, `executed`, `asset_return`, `turnover`, `transaction_cost`, `gross_return`, `net_return`, `gross_nav`, `net_nav`。

## 建议演示顺序

- 查看原始 CSV 前 6 行，解释 Bloomberg metadata 和 header row。
- 在真实转折处说明：RawSignal_t 使用截至 Close_t 的数据；Position_(t+1) 存在下一观测行，并归属于 Close_t→Close_(t+1) 的下一段 close-to-close 收益。明确这是假设能在 Close_t 附近实施的 end-of-day / same-close approximation，不是次日收盘或严格 next-open 成交。
- 展示首次从 Cash 入场时 turnover=1、cost=0.0005。
- 展示 `NAV / running_peak - 1` 和最大回撤。
- 运行 `python -m pytest -q` 并展示当前完整测试结果；同时说明核心计算测试与端到端编排/打包测试的覆盖边界。

不得在调试演示中临时改变参数或重新选择敏感性结果。
