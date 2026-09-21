# 测试报告序列化依赖

`python311` 保存 UE 5.8.2 自带 CPython 3.11 / Windows x64 对应的 orjson 3.12.0。仅验收脚本使用，游戏运行时不依赖 Python 或此库。包来源为 [orjson 官方 PyPI 页面](https://pypi.org/project/orjson/3.12.0/)，原包的许可证、METADATA、RECORD 与 SBOM 一并保留。

可重新安装：

```powershell
& .\Tools\Install-TestDependencies.ps1
```

安装仅写入项目的 `Tools/vendor/python311`，不改系统或引擎 Python。requirements 固定版本及 cp311-win_amd64 wheel 的 SHA-256。其他 Python 版本或平台不适用该二进制，测试脚本可明确回退标准库，性能采样必须注明实际序列化后端。

引入原因：增长的完整验收报告若在游戏线程使用标准库缩进输出，会显著阻塞 PIE。`Tools/benchmark_serializer.py` 用同一完整基线数据测试序列化与原子写盘，逐轮验证 JSON 还原结果完全相等，保留所有事件、断言与字段。实测结果在 `Saved/Acceptance/SerializerBenchmark.json`；该离线微基准不能替代最终游戏 CSV 帧时间采样。

orjson 对非有限浮点数的输出行为不同于标准库；验收数据必须拒绝非有限观测，不可将 NaN/Infinity 静默当作正常测量值。后端选择和实际保存耗时写入测试报告。
