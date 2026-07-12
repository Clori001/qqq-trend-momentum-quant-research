# Test Evidence

- Environment: `ccb_quant`
- Python: 3.12.13
- Command: `python -m pytest -q`
- Workspace、private archive 和 public archive 的最终结果由 `submission/package_audit.json` 及各包 manifest 动态记录。
- Public demo 的 skip 只允许来自未公开的冻结 daily artifacts 一致性测试。

覆盖范围包括：日期解析、字段验证、指标暖机 NaN、因果性、信号规则、月末决策、shift(1) 记账、已发生收益隔离、入场/出场/不变仓位、首次入场成本、成本仅扣一次、NAV 复利、绩效手算、共同比较期、主结果与稳健性对账、回撤序列一致性、图表 smoke test、完整 synthetic Phase 1-6、primary lookback 252→126、跨文件错配 fail-closed、动态报告元数据、manifest/ZIP 审计和 private/public 文件规则。

完整控制台输出另存为 `docs/pytest_output.txt`。Phase 7 文档和打包没有重新执行或改变 Phase 1-6 计算产物。
