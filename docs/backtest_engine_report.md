# 日频回测引擎报告 / Daily Backtest Engine Report

## 范围

本阶段只实现executed positions与逐日return engine，不计算aggregate metrics、robustness summary或charts。

## 固定公式

- `executed_position = raw_signal.shift(1)`
- `asset_return = Close.pct_change()`
- `turnover = abs(executed_position - executed_position.shift(1))`
- `cost_rate = transaction_cost_bps / 10000`
- `transaction_cost = turnover * cost_rate`
- `gross_return = executed_position * asset_return`
- `net_return = gross_return - transaction_cost`
- `gross_nav = (1 + gross_return).cumprod()`
- `net_nav = (1 + net_return).cumprod()`

## 比较区间与成本

- Common start: automatically derived from configured primary shifted signals
- Derived common start date: 2017-08-01
- Common comparison rows: 2247
- Primary transaction cost: 5 bps per unit turnover
- Position immediately before common start: Cash (0)
- Initial Long at common start: charged one entry cost
- Pre-common-period return/cost/NAV fields: preserved as NaN

## Primary daily strategies

- `BuyHold_RawSignal` remains separate from `BuyHold_ExecutedPosition`
- `MA20_60_RawSignal` remains separate from `MA20_60_ExecutedPosition`
- `TSMOM252_RawSignal` remains separate from `TSMOM252_ExecutedPosition`

## 未实现内容

- Aggregate performance metrics: not implemented
- Robustness summaries: not implemented
- Charts: not implemented
- Phase 4 engine status: PASS
