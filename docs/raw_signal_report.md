# 原始信号报告 / Raw Signal Report

## 范围

本阶段只生成raw signals。尚未应用shift、executed position、return、transaction cost、NAV、metric或chart。

## 规则

- `BuyHold_RawSignal = 1` on every observation.
- `MA20_60_RawSignal = 1` when `MA20 > MA60`, otherwise 0; indicator warm-up remains NaN.
- `TSMOM126_RawSignal`: on a valid completed month-end, 1 when `Momentum126 > 0`, otherwise 0; then forward-hold the raw decision until the next valid completed month-end.
  - Role: Pre-declared robustness only
  - First valid raw-signal date: 2017-01-31
  - Valid decision rows: 114
- `TSMOM252_RawSignal`: on a valid completed month-end, 1 when `Momentum252 > 0`, otherwise 0; then forward-hold the raw decision until the next valid completed month-end.
  - Role: Primary
  - First valid raw-signal date: 2017-07-31
  - Valid decision rows: 108

## 验证摘要

- Rows preserved: 2514
- MA raw-signal first valid date: 2016-10-03
- Terminal dataset month excluded as unconfirmed complete: True
- Strict MA tie rule: ties are Cash (0)
- Momentum zero rule: zero is Cash (0)
- Warm-up backfill before first valid decision: not used
- Executed positions or shift(1): not implemented
- Returns, costs, NAV, metrics, and charts: not implemented
- Phase 3 raw-signal status: PASS
