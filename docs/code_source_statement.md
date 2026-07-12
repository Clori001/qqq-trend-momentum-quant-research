# 代码与策略思想来源声明

## 代码来源

项目核心 Python 实现由研究者在 Codex 协助下为本项目编写，并通过确定性测试逐阶段审阅。未复制或调用 backtrader、vectorbt、bt、Backtesting.py、OpenBB 或 alphalens-reloaded 等一站式回测框架。pandas、NumPy、Matplotlib、PyYAML 和 pytest 仅作为通用运行或测试依赖。

## 策略思想参考

1. Moskowitz, T. J., Ooi, Y. H., & Pedersen, L. H. (2012). *Time Series Momentum*. Journal of Financial Economics, 104(2), 228-250. DOI: 10.1016/j.jfineco.2011.11.003. 本项目 Strategy 2 参考“资产自身过去收益方向决定下一期持仓”的核心思想，做单一 ETF、Long-Cash、252 个交易日回看、月度调仓的简化实现，不构成对原论文多资产期货、Long-Short 和波动率缩放策略的完整复现。

2. Faber, M. T. (2007). *A Quantitative Approach to Tactical Asset Allocation*. The Journal of Wealth Management, 9(4), 69-79. DOI: 10.3905/jwm.2007.674809. 本项目 Strategy 1 参考移动平均线趋势择时思想，将原文 10 个月单均线月度规则调整为日频 MA20/MA60 双线交叉规则，属于同一趋势择时思路下的不同实现，不是对原文方法的直接复现。

核验链接（访问日期：2026-07-12）：

- https://pages.stern.nyu.edu/~lpederse/papers/TimeSeriesMomentum.pdf
- https://www.pm-research.com/content/iijwealthmgmt/9/4/69

## 未使用的外部代码

上述论文只用于策略思想、差异说明和引用，没有从论文附属代码中复制实现。
