# 数据质量报告 / Data Validation Report

## 1. 数据源

- 文件：`data/raw/QQQ_US_Equity_20160710_Bloomberg_Raw.csv`
- SHA-256：`df1789c4a55d27f9a19733f0e798cf1f0f38152544bec8fa26fcefe43749cf42`
- 证券：QQQ US Equity
- 频率：daily observations on available trading dates
- 跳过Bloomberg元数据行：5
- 表头所在物理行：6
- Source date convention：`DD/MM/YYYY`
- Parsing rule：严格使用 `%d/%m/%Y`，不进行模糊日期推断
- Expected chronological range：2016-07-11 to 2026-07-10（验证通过）

## 2. 字段映射

| Source | Canonical |
|---|---|
| Dates | Date |
| PX_OPEN | Open |
| PX_HIGH | High |
| PX_LOW | Low |
| PX_LAST | Close |
| PX_VOLUME | Volume |

## 3. 验证结果

| Check | Result |
|---|---:|
| Raw observations | 2514 |
| Clean observations | 2514 |
| Exact duplicate rows found | 0 |
| Exact duplicate rows removed | 0 |
| Date range | 2016-07-11 to 2026-07-10 |
| Duplicate dates | 0 |
| Weekend rows | 0 |
| Missing values | 0 |
| Non-positive prices | 0 |
| OHLC violations | 0 |
| Negative volume rows | 0 |
| Zero volume rows | 0 |

## 4. 极端收益人工复核

阈值为绝对日收益 10%，仅用于触发人工复核。观察值不会仅因超过阈值而被删除；删除必须有独立的数据损坏证据。

| Date | Close return | Action |
|---|---:|---|
| 2020-03-16 | -11.98% | Retained - review only |
| 2025-04-09 | 12.00% | Retained - review only |

## 5. 价格口径与接纳结论

CSV无法单独证明 `PX_LAST` 的拆股、现金分红或total-return调整状态。因此后续研究只能保守地表述为基于 `PX_LAST` 的price-return结果，不得称为total return。

**Phase 1 data acceptance: PASS**

本报告只覆盖数据加载、清洗和验证；尚未实现任何策略、信号或回测。
