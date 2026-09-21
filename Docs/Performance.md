# 1080p High 性能采集与离线统计

本文件是可复现采样建议，不是实机性能结论。`Tools/tests/analyze_performance.py` 是无 UE 依赖的常规 Python 分析器；仅用合成 CSV 验证解析与公式，不把合成数据当作实机性能。正式 CSV 应由唯一编辑器执行者在实际 20 场 60 档运行中采集，不改变现有测试 capture 逻辑。

## 本地 UE 5.8.2 源码依据

- `Engine/Source/Runtime/Core/Private/ProfilingDebugging/CsvProfiler.cpp:1050` 附近：`CsvProfile STARTFILE=名称` 仅设置文件名；第二条 `CsvProfile START` 或 `CsvProfile FRAMES=N` 才调用 BeginCapture。`STOP` 结束采样；异步写出完成后再分析。默认目录由同文件 GetDefaultOutputDirectory 返回 `Saved/Profiling/CSV/`。
- `Engine/Source/Runtime/Launch/Private/LaunchEngineLoop.cpp:1518` 起：全局 `RenderThreadTime`、`GameThreadTime`、`GPUTime` 均转换为毫秒；另有 CriticalPath 等不同语义列。本分析默认选上述全局列，不将 CriticalPath 自动替换为普通线程时间。
- `Engine/Source/Runtime/RHI/Private/GPUProfiler.cpp:118`：`r.GPUCsvStatsEnabled` 默认 **0**。该文件约 1044 行起，启用后将主 Graphics queue 的细分 GPU stats 写入默认启用的 `GPU` 类别，多 GPU 为 `GPU2` 等；这些细分值不是可随意求和替代全局 GPUTime 的帧时间。
- `CsvProfiler.cpp:5098` 支持启动参数 `-csvGpuStats`，内部同样设 `r.GPUCsvStatsEnabled=1`。全局 GPUTime 仍依赖 RHI 的实际 timestamp 支持/结果；列存在但全零不能解释为 GPU 无耗时。

## 采集条件与命令

先记录显卡/驱动、CPU、构建版本、地图、是否 PIE、窗口实际分辨率、画质、VSync 与帧率上限。建议在独立 1920×1080 游戏窗口中测试；编辑器屏幕或截图尺寸不能证明渲染分辨率。关闭其他会控制角色的 runner，仅使用当前授权的 20 场执行者。窗口中执行并回读确认：

```text
r.SetRes 1920x1080w
sg.ViewDistanceQuality 2
sg.AntiAliasingQuality 2
sg.ShadowQuality 2
sg.GlobalIlluminationQuality 2
sg.ReflectionQuality 2
sg.PostProcessQuality 2
sg.TextureQuality 2
sg.EffectsQuality 2
sg.FoliageQuality 2
sg.ShadingQuality 2
sg.ResolutionQuality 100
r.ScreenPercentage 100
r.VSync 0
t.MaxFPS 60
r.GPUCsvStatsEnabled 1
```

质量级 2 为 High；100% screen percentage 用于明确内部采样尺度。PIE 嵌入视口可能不服从 r.SetRes，因此必须验证实际游戏窗口，必要时预先配置新编辑器游戏窗口为 1920×1080。项目当前 MotionBlur 默认关闭、Streaming.PoolSize=2048，正式报告须列明这些设置。保留纹理池/着色器编译警告，不能隐藏后声称稳定。

预热应在采样前完成并记录时长；若采样包含预热，只能用显式参数排除前 N 帧。不能自动剔除着色器长帧、加载卡顿或统计离群点。采集例：

```text
CsvProfile STARTFILE=Combat_1080pHigh_60.csv
CsvProfile START
```

实际测试完成后单独执行 `CsvProfile STOP`。也可用第二条 `CsvProfile FRAMES=3600` 做有界样本；这是帧数，不保证固定 60 秒。不要把 STARTFILE 和 START 合并成同一命令参数。确保 CSV 已完成写出，保留原始文件和测试 JSON 的时间关联。60 fps 上限会限制 FrameTime 的解释：可以评估达标/卡顿，不能由封顶样本推断无上限最高帧率。

## 分析命令与统计含义

```powershell
& 'D:\UEproject\Combat\Tools\.venv\Scripts\python.exe' 'D:\UEproject\Combat\Tools\tests\analyze_performance.py' 'D:\UEproject\Combat\Saved\Profiling\CSV\Combat_1080pHigh_60.csv' --warmup-frames 0 --output 'D:\UEproject\Combat\Saved\Acceptance\Performance_1080pHigh_60.json'
```

`--warmup-frames` 必填，0 表示不排除。需要剔除时写明实际 N 及理由；不按浮动帧率估算后暗中删帧。输入为未压缩 CSV；若列名不同，GPU 可使用 `--gpu-column` 指定精确列名，报告保留该选择，不猜测或拼合 pass。标准列缺失会明确 `missing_column`，不填零；空单元记录缺失行，异常或负数时间报错。重复表头及 UE 元数据行单独列出，不作为帧。

每列输出样本数、mean/median/p95/p99/max，及严格大于 16.7/20/33.3ms 的比例（0–1）。百分位在排序后的 `(N-1)*p` 处线性插值。1% low 定义为 `1000 / 最慢 ceil(N*0.01) 个样本毫秒均值`，并报告尾部样本数；它不是 `1000/p99`。只有 FrameTime 的该值可称交付帧率 1% low，GPU/线程同公式仅是耗时等效速率。所有长帧保留。报告包含原始 CSV 绝对路径、剔除数量与实际样本数，最终结论须等待真实数据。
