# ETF 趋势与时间序列动量回测研究报告

## 1. Executive Summary

本项目使用唯一获批的 Bloomberg QQQ 日频 CSV，研究透明的趋势和简化时间序列动量规则如何改变持有 QQQ 的历史风险收益特征。数据包含 2016-07-11 至 2026-07-10 的 2,514 个 available trading-date observations，未截短或删除观测。三条主策略在自动推导的共同期 2017-08-01 至 2026-07-10 上比较，共 2,247 个观测，主结果均扣除每单位换手 5 bps 成本。

Buy & Hold 的累计收益最高；Momentum252 的累计收益略低，但最大回撤较小、Calmar 较高；MA20/60 降低了年化波动率，但收益和 Sharpe 也较低。上述结果是历史 price-return 回测，不是预测或投资建议。

## 2. Test 3 and AI-Assisted Development Approach

项目按 Phase 1-7 分阶段完成。Codex 辅助生成和修订代码、测试、报告与图表；研究者逐阶段审批数据处理、参数、公式、稳健性范围和最终图表。任何策略参数均在主回测前声明；Momentum126 和成本敏感性从未被用于重新定义主策略。最终基线包含 42 项自动测试。

## 3. Data Source and Quality Controls

唯一源文件为 `data/raw/QQQ_US_Equity_20160710_Bloomberg_Raw.csv`，SHA-256 为 `DF1789C4A55D27F9A19733F0E798CF1F0F38152544BEC8FA26FCEFE43749CF42`。加载器跳过 5 行 Bloomberg metadata，使用物理第 6 行表头，将 Dates/PX_OPEN/PX_HIGH/PX_LOW/PX_LAST/PX_VOLUME 映射为 Date/Open/High/Low/Close/Volume。日期严格按 DD/MM/YYYY 解析并验证预期范围。

数据共有 2,514 行，无缺失值、重复日期、重复行、周末记录、非正价格、OHLC 逻辑错误或负成交量。2020-03-16 和 2025-04-09 的绝对日收益超过 10%，只触发人工复核并保留。CSV 无法证明 PX_LAST 的分红或 total-return 调整状态，因此研究只陈述为 price-return。

## 4. Strategy Design and Academic Reference

### 4.1 Buy & Hold

原始信号为 1，在共同期保持多头。首次从 Cash 进入 Long 时收取一次交易成本。

### 4.2 MA20/MA60 Trend

`MA20 > MA60` 时原始信号为 1，否则为 0；暖机期保持 NaN。本策略的择时逻辑参考 Faber (2007) 的移动平均趋势跟踪思想，但原文使用 10 个月单均线月度规则，本项目调整为日频 MA20/MA60 双线交叉，属于同一思路下的参数与频率简化，而非逐一复现。

### 4.3 Momentum252

`Momentum252 = Close / Close.shift(252) - 1`。在每个确认完成的月末读取指标，正数为 1，否则为 0，并 forward-hold 至下一有效月末。本策略参考 Moskowitz、Ooi 和 Pedersen (2012) 中“资产自身过去收益方向决定下一期持仓”的核心思想，但简化为单一 ETF、Long-Cash、252 日回看和月度调仓；不复现原论文的多资产期货、Long-Short 或波动率缩放。

## 5. Backtest Design and Look-Ahead Prevention

`RawSignal_t` 使用截至日期 t 收盘的完整数据计算。回测记账中，`Position_(t+1) = RawSignal_t`，`Return_(t+1) = Close_(t+1) / Close_t - 1`。因此，日期 t 的信号不会获得日期 t 已经发生的收益，而是被归属于下一段 close-to-close 收益区间；仓位值记录在下一观测行 t+1。资产收益为 `Close.pct_change()`；gross return 为执行仓位乘以资产收益；turnover 为执行仓位变化绝对值；net return 等于 gross return 减去 turnover 乘成本率。净值通过逐日复利计算。

该处理属于简化的 end-of-day / same-close implementation approximation，可理解为假设信号能够在日期 t 收盘附近实施。它不是次日收盘成交模型，也不是严格的 next-open 实盘执行模型；由于使用精确 `Close_t` 生成信号并作为下一收益区间起点，相比严格 next-open 执行可能存在一定乐观偏差。严格 next-open 或 next-close 模型只列为未来扩展，本轮不改变冻结研究结果。

共同起始日不硬编码，而从已配置主策略的最长有效暖机期自动推导。共同期前的收益、成本和 NAV 字段保持 NaN。主成本为 5 bps；现金收益为 0；年化使用 252 个交易观测；Sharpe 的主无风险利率为 0%。

## 6. Results and Risk Interpretation

| Strategy | Cumulative Return | Annualized Return | Annualized Volatility | Sharpe | Maximum Drawdown | Calmar | Trades | Time in Market |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Buy & Hold | 406.28% | 19.95% | 23.44% | 0.894 | -35.62% | 0.560 | 1 | 100.00% |
| MA20/60 Trend | 101.95% | 8.20% | 16.50% | 0.561 | -33.88% | 0.242 | 39 | 72.05% |
| Momentum252 | 337.06% | 17.99% | 21.17% | 0.888 | -28.56% | 0.630 | 5 | 87.09% |

Buy & Hold 在样本期内获得最高累计和年化收益，同时承受最高年化波动率和最深最大回撤。Momentum252 的年化收益由 Buy & Hold 的 19.95% 降至 17.99%，牺牲约 1.96 个百分点；最大回撤由 -35.62% 改善至 -28.56%，改善约 7.06 个百分点；Calmar 从 0.560 升至 0.630。因此它不是“收益更高”的策略，而是以相对有限的收益牺牲换取更明显的回撤改善。

MA20/60 的年化波动率比 Buy & Hold 低约 6.94 个百分点，但年化收益低约 11.75 个百分点，最大回撤只改善约 1.74 个百分点，Calmar 从 0.560 降至 0.242。它确实让净值波动更平缓，但没有有效改善最严重的资本损失，收益损失远大于风险改善。39 单位总换手只是部分原因；更重要的是退出后可能无法及时参与快速反弹。

年度路径进一步说明策略作用具有状态依赖性。2022 年净收益分别为 Buy & Hold -33.07%、MA20/60 -29.61%、Momentum252 -21.30%。Momentum252 在持续下跌趋势中逐渐退出，减少了该年的损失。但其最大回撤实际发生于 2020-03-16，说明低频动量可能应对缓慢形成的熊市，却无法提前避开突然的跳跃式冲击。

MA20/60 在 2020 年 3 月部分暴跌日处于 Cash，但也完全错过了 2020-03-13、03-17、03-24 和 04-06 分别约 8.47%、7.58%、7.74% 和 7.15% 的单日反弹。趋势策略的代价不仅是交易成本，也包括退出后无法及时重新参与快速反弹。这里不进行统计显著性或未来表现推断。

## 7. Robustness Checks

预声明稳健性包括 Momentum126/252 和 0/5/10 bps 成本。全部变体使用同一共同期。相对 0 bps，5 bps 使 Buy & Hold、MA20/60 和 Momentum252 的累计收益分别降低约 0.25、3.98 和 1.09 个百分点。这与总换手 1、39 和 5 一致，说明低频 Momentum 对固定成本更耐受。5 bps 下 Momentum126 年化收益 14.84%、Sharpe 0.809、最大回撤 -28.56%；Momentum252 年化收益 17.99%、Sharpe 0.888、最大回撤 -28.56%。这些结果只用于稳健性评价，没有选择“最佳”敏感性结果作为新主策略。

## 8. AI Collaboration, Debugging, and Verification

验证采用小型手算序列、synthetic full-pipeline fixtures 和冻结结果跨文件对账。确定性单元测试覆盖核心计算和结果一致性，包括暖机 NaN、因果性、同日已发生收益隔离、首次入场、成本、NAV、指标与回撤。阶段编排、配置切换、报告元数据和双版本打包流程另通过临时目录端到端测试验证；测试数量不应被解释为对所有代码路径的完全覆盖。

## 9. Limitations

- 单一 ETF 历史回测不能代表多资产组合或未来表现。
- PX_LAST 调整与分红状态未知，结果不能称为 total return。
- 固定 bps 成本不包含 bid-ask spread、市场冲击、税费或成交约束。
- Cash return 和 Sharpe risk-free rate 均固定为 0%，是项目假设而非市场利率预测。
- 不允许做空或杠杆；动量策略不是原论文的完整复现。
- 参数是预声明的示范参数，没有进行样本外检验或统计推断。
- end-of-day / same-close implementation approximation 使用精确 Close_t 作为下一收益区间起点，不是严格 next-open 或 next-close 成交模拟，可能存在乐观执行偏差。

## 10. Reproducibility and File Structure

项目可在 Windows Anaconda 环境 `ccb_quant` 中离线运行。`environment.yml` 固定关键依赖版本；`config/config.yaml` 保存研究参数；每个阶段读取上一阶段的已保存输出。`results/run_manifest.json` 记录提交文件和 SHA-256；`docs/test_evidence.md` 记录测试证据；`docs/reproducibility.md` 给出从新文件夹复现的命令。

## References

Faber, M. T. (2007). A Quantitative Approach to Tactical Asset Allocation. *The Journal of Wealth Management*, 9(4), 69-79. https://doi.org/10.3905/jwm.2007.674809

Moskowitz, T. J., Ooi, Y. H., & Pedersen, L. H. (2012). Time Series Momentum. *Journal of Financial Economics*, 104(2), 228-250. https://doi.org/10.1016/j.jfineco.2011.11.003
