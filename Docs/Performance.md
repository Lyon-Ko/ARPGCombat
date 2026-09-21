# 1080p High 性能采集与离线统计

本文件保留各阶段真实CSV、CPU诊断和可复现采样步骤。最终配置为Build14、Content `3787b6c`、Config `027dc88`。完整20场功能验收495/495通过；十场延后写盘采样平均16.6762ms、1%low56.9416fps，保留全部21,060帧、最大25.8148ms。两种保存条件的完整结果如下。`Tools/tests/analyze_performance.py` 无UE依赖；早期合成CSV仅用于验证解析公式。

## 最终配置正式20场实测

`arena_acceptance_20260921T202025583112Z.json`：495/495项通过，30/60fps各10场，17胜3败0超时。60fps的10场全部采用主动策略；30fps第10场为预先声明的被动败局。真实视口1920×1080、High2、100%采样、VSync0、MotionBlur0、Pool2048MB，Mass串行调度，Trace关闭。正式记录包含完整同步证据保存，所有慢帧原样保留。

原始 `Combat_1080pHigh_60_20260921T202025583112Z.csv` 与 `Performance_1080pHigh_60_20260921T202025583112Z.json` 保留22,829帧，warmup0：

| 实际 CSV 列（毫秒） | Mean | Median | p95 | p99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| FrameTime | 16.775437 | 16.6668 | 16.6734 | 19.120124 | 125.3702 |
| GPUTime | 3.057876 | 3.0008 | 3.52394 | 4.02584 | 5.5620 |
| RenderThreadTime | 0.046789 | 0.0007 | 0.0011 | 3.55266 | 7.3910 |
| GameThreadTime | 7.377873 | 6.9304 | 9.94018 | 19.284316 | 126.3179 |

FrameTime 1%low为 **37.8824fps**；>16.7 /20 /33.3ms分别为2.996189% /0.823514% /0.083227%，即19帧超过33.3ms。该正式记录存在长尾，不能声称无卡顿60fps。全轮1238次完整保存合计9.386671秒，最大单次18.156ms；同一Slate回调可以执行多条断言，每条check都会保存整份报告，因此最大单次保存不是单帧累计保存成本。

`HitchDetails_Final20.json` 列出全部>20ms帧及近邻阶段。最大125.3702ms帧处在第9场post_retry后一帧；第8/7/6场也有124.9812/119.0794/112.4344ms近邻帧。帧累计时间对齐存在异步采集边界误差，这支持检查同帧重试断言与保存的成本，但不单凭近邻关联将所有长帧归因于写盘。正式CSV不扣除这些帧。

## 最终配置十场延后写盘实测

`runtime_profile_20260921T203637661555Z.json` 采用相同固定游戏版本、1080p High、60fps封顶、Mass0、Trace关闭；完整事件与断言留在内存，489次save请求延后到CSV STOP并稳定2秒后写入。运行9场主动对战及第10场被动死亡，9胜1败0超时。253项中252通过，仅 `coverage.natural_projectile` 未满足，因此原报告状态为 **FAILED**；本轮没有自然触发剑气，不将采样可用冒充完整技能覆盖。剑气功能和自然覆盖以正式495/495及独立招式检查为证据。

`Performance_Supplemental_1080pHigh_60_20260921T203637661555Z.json` 分析全部 **21,060帧**，warmup0：mean **16.676207ms**、median16.6668ms、p9516.6709ms、p99 **16.781405ms**、max **25.8148ms**；1%low **56.9416fps**。>20ms共13帧（0.061728%），>33.3ms为0。原始CSV为 `Combat_Supplemental_1080pHigh_60_20260921T203637661555Z.csv`，46,466,157字节，包含全部对局、重试、工具回调与慢帧。

该结果表明此机器上的已采样实战接近60fps封顶节奏，并保留轻微帧波动。它仍含自动输入/事件观测开销，且没有自然剑气覆盖；不是无限场景性能保证。与正式CSV的预热、运行时刻和第10场策略不同，不能把两者全部差异都归因于写盘。正式完整同步保存记录与补充记录并列保留。最终冷启动359项与暂停交接12项另有报告；暂停截图不作为性能证据。

## 首轮基线实测（修复前）

- 对局报告：`Saved/Acceptance/arena_acceptance_20260921T185232088295Z.json`，20 场已完成；唯一重试位置断言失败，整轮验收未通过。
- 原始 CSV：`Saved/Profiling/CSV/Combat_1080pHigh_60_20260921T185232088295Z.csv`。
- 分析结果：`Saved/Acceptance/Performance_1080pHigh_60_20260921T185232088295Z.json`。
- 采样为 1080p High、60 fps 封顶阶段的 10 场，包括重置、测试回调、JSON 保存及慢帧。22,071 帧，明确 `--warmup-frames 0`，全部保留；四个指标均无缺失或全零样本。尾部扩展表头与元数据不是帧，分析器已在报告单独记录。

| 实际 CSV 列（毫秒） | Mean | Median | p95 | p99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| FrameTime | 17.8530 | 16.6668 | 16.6771 | 63.7491 | 755.3069 |
| GPUTime | 3.3633 | 3.2149 | 4.3998 | 5.5347 | 7.2519 |
| RenderThreadTime | 0.0882 | 0.0007 | 0.0012 | 3.9370 | 6.5707 |
| GameThreadTime | 8.6440 | 7.0562 | 10.1979 | 64.2826 | 756.5827 |

FrameTime 的 **1% low 为 9.5732 fps**，依据最慢 221 帧的均值；严格超过 16.7 / 20 / 33.3 ms 的帧比例分别为 **3.1942% / 1.9664% / 1.7761%**。GPU 与线程列不是交付帧率，也不能简单相加；RenderThreadTime 的极低中位数按真实全局计时列原样列出，不以此推断渲染工作总成本。

本基线有明显长帧：p95 接近封顶节奏，但 p99 和最大帧显著升高，不能宣称“稳定 60 fps”。GameThreadTime 也有长尾；单凭汇总不能把全部长帧归因于游戏逻辑或测试器。后续分别测量了完整历史 JSON 同步保存和 Mass 编辑器等待，结果见后文；原始慢帧未删除、扣除或改写。

后续Runtime的重置计时修复提交为 `9829376`，`Saved/Build_ResetTiming_11.log` 编译PASS（17.23秒）。上述CSV早于该修复；下面继续保留13版历史统计，当前最终结果见本页开头。

## 13版正式20场实测

正式报告 `Saved/Acceptance/arena_acceptance_20260921T192140351854Z.json` 已通过469/469项：30/60 fps各10场，17胜3败0超时（主动17胜2败，被动1败），cleanup_errors=null。原始CSV为 `Saved/Profiling/CSV/Combat_1080pHigh_60_20260921T192140351854Z.csv`，分析为 `Saved/Acceptance/Performance_1080pHigh_60_20260921T192140351854Z.json`。Source `4542b8d`、Content+tests `10fb1ac`，Build13通过。

1080p High、60fps封顶阶段保留全部22,910帧，`--warmup-frames 0`：FrameTime mean **16.809291ms**、median **16.6668ms**、p95 **16.6732ms**、p99 **19.693029ms**、max **122.4849ms**。1%low **33.7397fps**，最慢230帧均值取倒数；严格>16.7 /20 /33.3ms占 **2.758621% /0.916630% /0.183326%**。GPUTime mean3.072695ms、p994.068066ms，存在真实GPU列，没有推断缺失数据。

本轮正式测试仍执行1217次完整同步证据保存，总耗时9.044016秒，最大单次18.9055ms（序列化累计6.982404秒，写入2.061611秒）。这些是实际测试器成本，**不能将全部长帧归因于保存**，也不从帧统计扣除。结果明显优于旧基线，但最大122.4849ms和1%low仍揭示长尾，不能写成稳定无卡顿60fps或无上限性能。

## 延后写盘与GC观测补充实测

两份补充均为同1080p High、60fps封顶、三场真实自然对局（第3场预设被动死亡），采样期间完整事件留内存，CSV STOP并落稳后一次完整保存。它们不替代正式20场，也不删除或修正正式CSV。每份均warmup0，保留全部长帧。

| 报告（Saved/Acceptance） | 覆盖结果 | 帧数 | FrameTime mean / p99 / max (ms) | 1%low (fps) |
| --- | --- | ---: | ---: | ---: |
| `runtime_profile_20260921T193559409889Z.json` | 148/149，三场没有自然剑气，coverage.natural_projectile FAIL | 6377 | 16.705475 / 16.701764 / 48.4579 | 48.7492 |
| `gc_profile_20260921T194436862733Z.json` | 149/149 PASS | 6219 | 16.717636 / 16.71002 / 63.6397 | 46.1384 |

首份分析为 `Performance_Supplemental_1080pHigh_60_20260921T193559409889Z.json`，>20/33.3ms占0.250902%/0.094088%；缺技能覆盖的失败保留，不因CSV可用便改成PASS。第二份完整统计嵌于 `GCAnalysis_20260921T194436862733Z.json`，>20/33.3ms占0.257276%/0.096479%。原始CSV路径均在分析报告中。

GC观测保持原GC策略，记录采样回调tick最大约1.533ms、Python GC最大约7.387ms；未发现与主要长帧的关联。CSV起点加累计FrameTime的对齐可能有一帧偏差，最近事件不证明因果；不能将剩余长尾归因于GC、关闭GC或扣除慢帧。观测hook已移除。两次补充表明延后整份报告写盘时仍有48–64ms长帧；原因继续诊断，不能宣称稳定无卡顿60fps。方法见 [RuntimeProfile](RuntimeProfile.md)。

## Mass编辑器等待与项目调度选择

`Saved/Acceptance/MassWaitDiagnosis_20260921T200209859752Z.json` 对完整6308帧Insights记录的导出显示，Mass编辑器tick最大64.0657ms；前五个长帧86.45/56.26/49.35/49.02/48.34ms对应Mass范围64.07/34.73/31.40/33.27/28.49ms。例如 `Saved/Profiling/Traces/longframe_5449/TimingEvents.csv` 的56.2641ms帧包含MassEntityEditorSubsystem 34.7317ms，内部阶段任务等待34.6972ms、DuringPhysics队列等待28.888ms。这支持已捕获长帧中Mass编辑器任务等待占主要范围；不是对所有卡顿的普遍归因。

控制采样 `Performance_MassSingleThread_1080pHigh_60_20260921T201336033106Z.json` 使用同三场工具，仅设 `mass.FullyParallel=0`，结束恢复原值1。5518帧全部保留：mean16.677ms、p9916.718ms、max29.176ms、1%low56.609fps，>33.3ms为0。三场2胜1败，162项中161通过、natural_projectile覆盖失败保留。它不替代正式20场，也不能称为严格同构战斗序列AB：旧13采样与修复后的14默认链不同，Insights14采样另有trace开销。原始报告与失败均不修改。

基于上述源码与实测，本工程在 `Config/DefaultEngine.ini` 的 `[ConsoleVariables]` 设置 `mass.FullyParallel=0`。该选择保留Mass处理器执行，仅改为串行调度；不关闭StateTree、插件、画质或GC。`MassProcessingPhaseManager.cpp:36` 定义该普通CVar，`:576–585` 在阶段边界切换执行模式，`:154` 保留单线程处理器调用。`MassEntityEditorSubsystem.cpp:183–193` 每帧派发阶段任务并等待；EditorEngine.cpp:1557固定加载该编辑器模块，因此没有用禁插件替代。

项目section支持延迟CVar注册：`Core/Private/Misc/ConfigCacheIni.cpp:6971` 从GEngineIni应用ConsoleVariables；`Core/Private/HAL/ConsoleManager.cpp:3328–3343` 将CreatedFromIni占位值传给后续注册的非Cheat变量。`MassSerialColdStart_20260921T201915630167Z.json` 已在重启后回读0；最后一次 `FinalColdStart_20260921T204520545958Z.json` 也确认该值、默认地图、33蓝图、216资产和默认四连。正式runtime_metadata只读记录Mass开关、named-events策略及Trace状态；策略值不等于跟踪已激活。

CPU trace 诊断的原始 `trace_profile_20260921T200209859752Z.json` 状态为 FAILED：三场实际执行的154项断言通过，但工具将异步 `Trace.Stop` 当作同步操作检查，导致停止阶段失败。原始 trace、CSV 与失败状态全部保留；后续检查确认连接停止，工具已改为跨帧等待断开。ContextSwitch 的操作系统跟踪权限被拒绝，因此该记录只支持引擎 CPU scope 分析，不支持操作系统线程调度归因。它带有 trace/named-events 采集开销，不作为无跟踪运行的性能成绩。

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

每列输出样本数、mean/median/p95/p99/max及严格大于16.7/20/33.3ms的比例（0–1）。百分位在排序后的 `(N-1)*p` 处线性插值。1%low定义为 `1000 / 最慢 ceil(N*0.01) 个样本毫秒均值`，并报告尾部样本数；它不是 `1000/p99`。只有FrameTime的该值表示交付帧率，GPU/线程同公式仅是耗时等效速率。所有长帧保留，报告包含原始CSV绝对路径、剔除数量与实际样本数。
