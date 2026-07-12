# PUBLIC DEMO — BLOOMBERG DATA NOT INCLUDED

# AI 辅助 ETF 趋势与时间序列动量回测系统

本项目是建行 Test 3（大型模型 AI 编程工具）候选项目。系统使用唯一获批的离线 Bloomberg QQQ CSV，完成数据验证、指标、原始信号、滞后一行执行、交易成本、净值、绩效指标、预声明稳健性检查与可视化。

## 快速开始（Windows / Anaconda Prompt）

```powershell
conda env create -f environment.yml
conda activate ccb_quant
python -m pytest -q
```

当前工程收口后的完整测试结果由每个 ZIP 内的 manifest 和 `submission/package_audit.json` 动态记录。原有确定性测试覆盖核心计算和结果一致性；新增测试覆盖临时目录完整流水线、配置切换、输入错配 fail-closed、严格 Boolean 解析、冻结快照、archive exact membership、public allowlist 与双版本打包审计。阶段编排、报告和打包不能仅以单元测试数量概括，另通过端到端复现验证。

若要从原始 CSV 按阶段复现，必须从项目根目录依次运行：

```powershell
python main.py --config config/config.yaml
python phase2_indicators.py --config config/config.yaml
python phase3_signals.py --config config/config.yaml
python phase4_backtest.py --config config/config.yaml
python phase5_metrics.py --config config/config.yaml
python phase6_visualizations.py --config config/config.yaml
```

最终执行路径不需要互联网，也不依赖 Bloomberg Excel 公式。所有路径均相对于项目根目录。

## 数据输入

- 唯一数据源：`data/raw/QQQ_US_Equity_20160710_Bloomberg_Raw.csv`
- 证券：QQQ US Equity
- 日期：2016-07-11 至 2026-07-10
- 频率：available trading dates 上的 daily observations
- 原始日期格式：`DD/MM/YYYY`
- 原始文件不会被覆盖或截短

`PX_LAST` 是否包含拆股、现金分红或 total-return 调整，无法仅凭 CSV 证明。因此报告只使用“基于 PX_LAST 的 price-return”表述。

## 策略和时点

1. Buy & Hold：原始信号始终为 1。
2. MA20/MA60：当 `MA20 > MA60` 时为 1，否则为 0；原文 Faber (2007) 使用 10 个月单均线月度规则，本项目是日频双均线简化实现，不是直接复现。
3. Momentum252：月末读取过去 252 个交易观测收益的正负，正数为 1，否则为 0，并持有至下一次有效月末；这是 Moskowitz、Ooi 和 Pedersen (2012) 核心思想的单 ETF、Long-Cash 简化实现。

所有策略的记账关系为：

```text
executed_position = raw_signal.shift(1)
```

`RawSignal_t` 使用截至日期 t 收盘的完整数据计算。回测记账中，`Position_(t+1) = RawSignal_t`，`Return_(t+1) = Close_(t+1) / Close_t - 1`。因此，日期 t 的信号不会获得日期 t 已经发生的收益，而是被归属于下一段 close-to-close 收益区间；仓位值记录在下一观测行 t+1。

该处理属于简化的 end-of-day / same-close implementation approximation，可理解为假设信号能够在日期 t 收盘附近实施。它不是次日收盘成交模型，也不是严格的 next-open 实盘执行模型；由于使用精确 `Close_t` 生成信号并作为下一收益区间起点，相比严格 next-open 执行可能存在一定乐观偏差。严格 next-open 或 next-close 模型只作为未来扩展。

主结果采用每单位换手 5 bps 成本、现金收益 0、Sharpe 无风险利率 0%、252 个交易观测年化。

## 结果口径

三条主策略使用自动推导的同一比较期：2017-08-01 至 2026-07-10，共 2,247 个观测。`results/performance_summary.csv` 是主绩效表；`results/robustness_summary.csv` 仅用于 126/252 日动量和 0/5/10 bps 成本的预声明稳健性分析，不用于重新选择主策略。

## 目录

- `config/`：研究与输出配置
- `data/raw/`：不可变 Bloomberg 输入
- `data/processed/`：清洗、指标和信号数据
- `src/ccb_quant/`：分阶段核心模块
- `tests/`：确定性与跨文件一致性测试
- `results/`：日频结果、汇总、稳健性和四张最终图
- `docs/`：方法、决策、AI 使用、调试与复现文档
- `logs/`：各阶段运行日志
- `output/pdf/`：最终项目报告 PDF

## 关键限制

- 历史回测不是预测、投资建议或实盘成交模拟。
- 研究仅覆盖单一 ETF，不含做空、杠杆、利息、滑点或市场冲击。
- 价格调整和分红口径未知，不能称为 total return。
- 交易成本是固定 bps 简化模型。
- end-of-day / same-close approximation 不是严格可成交价格模拟，可能相对 next-open 执行偏乐观。
- Bloomberg 数据不得上传到公共仓库；提交与共享须遵守数据许可。

完整方法见 `docs/methodology_report.md`，复现和审计步骤见 `docs/reproducibility.md`。
