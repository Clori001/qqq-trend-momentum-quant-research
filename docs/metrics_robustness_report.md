# Phase 5 Metrics and Robustness Report

## Methodology

- Common comparison start: 2017-08-01 (automatically derived in Phase 4)
- Common daily observations: 2247
- Annualization: 252 trading observations
- Sharpe annual risk-free rate: 0.0%
- Phase 4 daily input SHA-256: CFAEC7F04CAF2B62DE87339E7ACB227A53DCFEBADF76A062B975CA4D46195126
- Phase 3 raw-signal input SHA-256: FA5981882AA7D16E38F7B7D54E0463F7F2D5D5FF6B11587F4BF990658E15E26B
- Primary results: net returns at 5 bps per unit turnover
- Trade count: number of executed-position changes where turnover > 0
- Entries/exits: positive/negative executed-position changes, including initial entry from Cash
- Maximum drawdown: minimum of NAV / running peak - 1, with initial capital 1 included

## Output scope

- Primary summary rows: 3
- Pre-declared robustness rows: 12
- Primary net drawdown series saved separately for the later chart phase
- Robustness grid: Buy & Hold, MA20/60 Trend, Momentum126, Momentum252 at configured cost sensitivities
- Sensitivity results are not used to redefine the primary strategy
- Charts: not implemented in Phase 5
- Phase 5 status: PASS
