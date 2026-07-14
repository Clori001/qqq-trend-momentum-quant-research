# PUBLIC DEMO — BLOOMBERG DATA NOT INCLUDED

**English** | [中文](README.zh-CN.md)

![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white) ![pandas 3.0.1](https://img.shields.io/badge/pandas-3.0.1-150458?logo=pandas&logoColor=white) ![NumPy 2.3.5](https://img.shields.io/badge/NumPy-2.3.5-013243?logo=numpy&logoColor=white) ![Matplotlib 3.11](https://img.shields.io/badge/Matplotlib-3.11-11557C?logo=python&logoColor=white) ![pytest 9.1](https://img.shields.io/badge/pytest-9.1-0A9EDC?logo=pytest&logoColor=white)

# ETF Trend-Following and Time-Series Momentum Backtesting System

This project was developed for an internship selection assignment. Using a single approved offline Bloomberg QQQ CSV, the system performs data validation, indicator calculation, raw-signal generation, one-row-lagged execution, transaction-cost modeling, NAV calculation, performance evaluation, pre-declared robustness checks, and visualization.

## Quick Start

Create and activate the environment in Anaconda Prompt on Windows, then run the tests:

```powershell
conda env create -f environment.yml
conda activate ccb_quant
python -m pytest -q
```

The finalized project records complete test results dynamically in each ZIP manifest and in `submission/package_audit.json`. Deterministic tests cover core calculations and cross-result consistency. Additional tests cover a full temporary-directory pipeline, configuration switching, fail-closed input mismatch handling, strict Boolean parsing, frozen snapshots, exact archive membership, the public allowlist, and dual-package audits. Phase orchestration, reporting, and packaging are also validated through end-to-end reproduction rather than represented only by a unit-test count.

To reproduce the pipeline phase by phase from the raw CSV, run the following commands in order from the project root:

```powershell
python main.py --config config/config.yaml
python phase2_indicators.py --config config/config.yaml
python phase3_signals.py --config config/config.yaml
python phase4_backtest.py --config config/config.yaml
python phase5_metrics.py --config config/config.yaml
python phase6_visualizations.py --config config/config.yaml
```

The final execution path requires no internet connection and does not depend on Bloomberg Excel formulas. All paths are relative to the project root.

## Data Input

- Sole data source: `data/raw/QQQ_US_Equity_20160710_Bloomberg_Raw.csv`
- Security: QQQ US Equity
- Date range: 2016-07-11 to 2026-07-10
- Frequency: daily observations on available trading dates
- Raw date format: `DD/MM/YYYY`
- The raw file is never overwritten or truncated

The CSV alone cannot establish whether `PX_LAST` includes adjustments for splits, cash dividends, or total return. The report therefore uses only the term “price return based on `PX_LAST`.”

## Strategies and Timing

1. **Buy & Hold:** the raw signal is always 1.
2. **MA20/MA60:** the signal is 1 when `MA20 > MA60`, and 0 otherwise. Faber (2007) uses a monthly rule based on a single 10-month moving average; this project uses a simplified daily dual-moving-average implementation and is not a direct replication.
3. **Momentum252:** at each month-end, the strategy checks the sign of the return over the previous 252 trading observations. A positive return produces a signal of 1; otherwise, the signal is 0. The position is held until the next valid month-end. This is a simplified single-ETF, Long-Cash implementation of the central idea in Moskowitz, Ooi, and Pedersen (2012).

The accounting relationship for every strategy is:

```text
executed_position = raw_signal.shift(1)
```

`RawSignal_t` is calculated using all data available through the close of date t. In the backtest accounting, `Position_(t+1) = RawSignal_t` and `Return_(t+1) = Close_(t+1) / Close_t - 1`. A signal generated on date t therefore receives the next close-to-close return interval and is recorded on observation row t+1.

This is a simplified end-of-day / same-close implementation approximation. It is neither a next-close execution model nor a strict next-open live-trading model. Because `Close_t` is used both to generate the signal and as the starting point of the next return interval, results may be somewhat optimistic relative to strict next-open execution. Strict next-open or next-close models are reserved for future extensions.

Primary results assume a transaction cost of 5 bps per unit of turnover, a cash return of 0, a Sharpe risk-free rate of 0%, and annualization based on 252 trading observations.

## Result Definition

All three primary strategies use the same automatically derived comparison period: 2017-08-01 to 2026-07-10, totaling 2,247 observations. `results/performance_summary.csv` is the primary performance table. `results/robustness_summary.csv` is used only for pre-declared robustness analysis across 126/252-day momentum windows and 0/5/10 bps transaction costs; it is not used to reselect the primary strategy.

## Repository Structure

| Path | Description |
|---|---|
| `config/` | Research and output configuration |
| `data/raw/` | Immutable Bloomberg input |
| `data/processed/` | Cleaned data, indicators, and signals |
| `src/ccb_quant/` | Phase-based core modules |
| `tests/` | Deterministic and cross-file consistency tests |
| `results/` | Daily results, summaries, robustness outputs, and four final figures |
| `docs/` | Methodology, decisions, AI-use, debugging, and reproducibility documentation |
| `logs/` | Per-phase execution logs |
| `output/pdf/` | Final project report PDF |

## Key Limitations

- Historical backtests are not forecasts, investment advice, or simulations of live execution.
- The study covers a single ETF only and excludes short selling, leverage, interest, slippage, and market impact.
- The treatment of price adjustments and dividends is unknown, so results must not be described as total return.
- Transaction costs use a simplified fixed-bps model.
- The end-of-day / same-close approximation is not a strict executable-price simulation and may be optimistic relative to next-open execution.
- Bloomberg data must not be uploaded to a public repository; all submission and sharing must comply with the applicable data license.

See `docs/methodology_report.md` for the full methodology and `docs/reproducibility.md` for reproduction and audit procedures.
