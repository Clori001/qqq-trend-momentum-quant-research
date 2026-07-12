# Reproducibility Guide

## 前提

- Windows 10/11
- Anaconda 或 Miniconda
- 项目完整复制到一个可写的新文件夹
- 离线源文件位于 `data/raw/QQQ_US_Equity_20160710_Bloomberg_Raw.csv`

不要从公共仓库下载或上传 Bloomberg 数据。

## 环境与测试

在 Anaconda Prompt 中进入项目根目录：

```powershell
conda env create -f environment.yml
conda activate ccb_quant
python -m pytest -q
```

预期结果以对应包内 manifest 为准。Public demo 因许可数据缺失会跳过 4 项冻结日频结果一致性测试，其余测试必须通过。

## 分阶段复现

```powershell
python main.py --config config/config.yaml
python phase2_indicators.py --config config/config.yaml
python phase3_signals.py --config config/config.yaml
python phase4_backtest.py --config config/config.yaml
python phase5_metrics.py --config config/config.yaml
python phase6_visualizations.py --config config/config.yaml
```

每一步只依赖上一步的已保存文件；图表模块不重新计算指标、信号、仓位或绩效。

## 审计检查

```powershell
Get-FileHash data\raw\QQQ_US_Equity_20160710_Bloomberg_Raw.csv -Algorithm SHA256
python -m pytest tests\test_phase5_consistency.py -q
```

原始文件预期 SHA-256：`DF1789C4A55D27F9A19733F0E798CF1F0F38152544BEC8FA26FCEFE43749CF42`。

## 复现边界

- 运行阶段脚本会覆盖相应 generated outputs 和日志；提交审阅时应先保留冻结包。
- CSV 是唯一市场数据来源；不访问网络或 Bloomberg 终端。
- 由于 PX_LAST 调整状态未知，复现的是 price-return 研究结果。
