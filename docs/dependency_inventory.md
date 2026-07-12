# Dependency Inventory

| Package | Version | Scope | Purpose |
|---|---:|---|---|
| Python | 3.12 | Runtime | 语言运行时 |
| pandas | 3.0.1 | Runtime | CSV、时间序列、滚动指标、表格输出 |
| numpy | 2.3.5 | Runtime | 数值计算与确定性比较 |
| matplotlib | 3.11.0 | Runtime | 四张最终 PNG 图 |
| PyYAML | 6.0.3 | Runtime | 读取 `config/config.yaml` |
| pytest | 9.1.1 | Test | 42 项自动测试 |
| reportlab | 4.4.9 | Phase 7 build | 生成最终 PDF 报告；不影响回测 |
| pypdf | 6.10.0 | Phase 7 QA | PDF 页数与文本结构检查；不影响回测 |

未使用一站式回测框架。最终回测执行不需要互联网。`reportlab` 和 `pypdf` 只服务于提交报告构建与验证。
