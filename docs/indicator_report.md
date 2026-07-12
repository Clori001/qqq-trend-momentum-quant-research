# 指标计算报告 / Indicator Calculation Report

## 范围

本阶段只计算trailing indicators，不包含strategy signal、position、return、cost或backtest。

## 公式与有效日期

- `MA20 = Close.rolling(20, min_periods=20).mean()`
  - Warm-up NaN rows: 19
  - First valid date: 2016-08-05
- `MA60 = Close.rolling(60, min_periods=60).mean()`
  - Warm-up NaN rows: 59
  - First valid date: 2016-10-03
- `Momentum126 = Close / Close.shift(126) - 1`
  - Role: Pre-declared robustness indicator only
  - Warm-up NaN rows: 126
  - First valid date: 2017-01-09
- `Momentum252 = Close / Close.shift(252) - 1`
  - Role: Primary indicator
  - Warm-up NaN rows: 252
  - First valid date: 2017-07-11

## 完整性检查

- Input/output rows: 2514 / 2514
- All MA and momentum lookbacks: read from `config/config.yaml`
- Primary momentum indicator: Momentum252
- Pre-declared robustness momentum indicators: Momentum126
- Robustness indicators do not redefine the primary indicator
- Current and past Close values only: deterministic tests passed
- Centered windows: not used
- Warm-up backfill: not used
- Source OHLCV columns changed: no
- Phase 2 indicator status: PASS
