# 最终交付证据说明

正式验收以 `arena_acceptance_20260921T202025583112Z.json` 为主：**495 / 495 断言通过，20 场，17 胜、3 败、0 超时**。30 / 60 FPS 上限各运行 10 场；3 次战败中含 1 场预设的被动死亡覆盖，战败结果不等于测试断言失败。这是工程内 PIE 自动化验收，不代表人工试玩评价或独立发行包验收。

本轮版本：Source `4542b8d`、Content `3787b6c`、Config `027dc88`、Build 14。旧版本报告和单项报告各有自己的适用范围，不能替代本轮主报告。

`manifest.json` 记录实际收录文件、原始路径、大小、SHA-256和存储方式，并直接从正式报告提取主判定。下列结果均有实际运行证据；各自的失败和范围保留。

本次实际归档85项：70份字节副本、10份完整CSV的无损gzip、5项本地大文件引用。复制、gzip容器、解压内容与本地引用均已独立核对SHA，见 [校验记录](../DeliveryArchiveVerification_20260922.json)；完整调用参数见 [命令记录](../CurateDeliveryCommand_20260922.json)。Git对证据目录关闭换行转换和空白清理，保存原始字节；PNG继续使用Git LFS。80份可移植文件的暂存Git内容或LFS OID也已逐项核对，见 [Git校验](../GitIndexVerification_20260922.json)。

## 报告范围

| 用途 | 报告 | 已核实结果与范围 |
| --- | --- | --- |
| 正式主验收 | `arena_acceptance_20260921T202025583112Z.json` | 495 / 495；20 场，17 胜、3 败、0 超时 |
| 正式性能 | `Performance_1080pHigh_60_20260921T202025583112Z.json` | 上述正式测试的 1080p、High、60 FPS 上限 CSV；保留全部 22,829 个数值帧 |
| 新技能扩展 | `SkillExtensionFinal_20260921T195256502504Z.json` | 21 / 21；新技能配置与默认配置恢复验证 |
| 默认四连段 | `default_chain_only_20260921T195607760663Z.json` | 29 / 29；真实按键输入，30 / 60 FPS 下四连段及 104 点总伤害 |
| AI 场景 | `arena_ai_scenarios_20260921T193914Z.json` | 701 / 701；单项场景覆盖，保留其原版本范围 |
| AI 近距离 | `arena_ai_near_20260921T194032Z.json` | 258 / 258；近距离行为覆盖，保留其原版本范围 |
| 空间与镜头 | `arena_spatial_visual_20260921T194122Z.json` | 15 / 15；空间与镜头夹具验证 |
| 延后写盘的10场补充 | `runtime_profile_20260921T203637661555Z.json` | 252/253；9胜1被动败0超时，唯一自然剑气覆盖失败保留；全部21,060帧可用 |
| 最终冷启动核查 | `FinalColdStart_20260921T204520545958Z.json` | 359/359；216资产、33BP、39Montage、实际默认地图、四连、DLL与Mass设置 |
| 最终试玩交接 | `FinalHandoff_20260921T204548707031Z.json` | 12/12；1080p High、双方满血、暂停、按键释放与全部回调清理；P继续 |
| 最终画面检查 | `FinalVisualReview_20260921T204648Z.json` | 协调者实际激活并查看原生PIE窗口；接受00011暂停界面与00010自然战斗画面 |

## 正式性能读数

原始文件为 `Saved/Profiling/CSV/Combat_1080pHigh_60_20260921T202025583112Z.csv`。分析使用 `--warmup-frames 0`，未裁剪异常值、删除长帧或排除预热帧。

| 指标 | 数值 |
| --- | ---: |
| 保留数值帧 | 22,829 |
| 平均帧时间 | 16.775437 ms |
| P99 帧时间 | 19.120124 ms |
| 最大帧时间 | 125.3702 ms |
| 1% low | 37.8824 FPS |

1% low 按最慢 `ceil(N × 0.01)` 帧的平均帧时间取倒数。最大长帧仍保留在统计中，以上结果不表示每帧均达到 60 FPS。PIE、自动输入与观测工具均属于测试条件；额外 Trace 采样会增加观测开销，其诊断结果应与正式 CSV 分开解释。

最终十场延后写盘的分析为 `Performance_Supplemental_1080pHigh_60_20260921T203637661555Z.json`：全部21,060帧，mean16.676207ms、p9916.781405ms、max25.8148ms、1%low56.9416fps；>20ms共13帧，>33.3ms为0。完整事件和断言在内存保留，489次保存请求延后到STOP后稳定再写。该轮缺少自然剑气触发，报告仍为FAILED；正式495通过不受影响。两轮预热、运行时刻和第10场策略不同，不把全部性能差异都归因于写盘。详细方法见 [Performance](../../Performance.md)。

## 保留的失败诊断

- `trace_profile_20260921T200209859752Z.json`：3 场采样执行的 154 / 154 断言通过，但工具在 `Trace.Stop` 尚未异步断开时按同步结果判定失败，因此原报告仍为 **FAILED**。后续成功断开和可用的原始 Trace 不会把这份报告升级为通过，也不构成正式 20 场验收。
- `MassSingleThread_20260921T201336033106Z.json`：3 场补充样本为 161 / 162 断言通过，`coverage.natural_projectile` 失败，原报告仍为 **FAILED**。样本量和覆盖限制原样保留。
- `runtime_profile_20260921T203637661555Z.json`：最终十场补充252/253，唯一自然剑气覆盖失败，完整帧统计及原FAILED一起保留。
- `Combat_FinalColdStart_20260922.log`：3个引擎Core格式化自测共13条断言失败，工程冷启动359项另行通过；来源与本地化敏感断言说明见 [EngineStartupNotes](../../EngineStartupNotes.md)。未修改引擎或语言掩盖错误。
- 更早的扩展探针与验收报告保留各自结果。旧 `defaults_restored` 观察曾被后续独立标签与磁盘重载验证推翻；旧 192140 批次也未精确检查修复后的默认四连段。最终结论依据上面的新主报告。

## 文件保存与复算

归档工具对报告、日志和图片执行字节一致复制，并校验复制前后的 SHA-256。原始 CSV 仅以无损 gzip 保存，解压后的 SHA-256 必须匹配原文件；gzip 不删除任何数值帧。CSV 中重复表头或元数据行由分析器识别，不能当作删除游戏帧。

大文件使用 `local_reference_only`：manifest 记录其项目内原始路径、大小和 SHA-256，不把媒体本体复制或压缩进证据目录。它们必须随原工程另行保留，单独带走本目录无法还原这些文件：

- `Saved/Acceptance/CombatNativeFocusedOutput.wav`：实际 UE 主输出录音；属于自动化音频证据，不声称人工听审过每个效果。
- `Saved/Profiling/Traces/Combat_TraceObserved_1080pHigh_60_20260921T200209859752Z.utrace`：528,052,820 字节的原始 Trace；保留供 Unreal Insights 复查。

归档完成后，可从工程根目录运行以下 PowerShell 示例。`$pythonExe` 使用本机现存解释器；其他机器请替换该路径。恢复目标以 `xb` 创建，已有同名文件时会拒绝覆盖。

```powershell
Set-Location 'D:\UEproject\Combat'
$pythonExe = 'D:\UEproject\Combat\Tools\.venv\Scripts\python.exe'
$archive = 'Docs/Evidence/Final_20260922/Combat_1080pHigh_60_20260921T202025583112Z.csv.gz'
$restored = 'Saved/Acceptance/Restored_Final20_20260921T202025583112Z.csv'
@'
import gzip, shutil, sys
with gzip.open(sys.argv[1], 'rb') as source, open(sys.argv[2], 'xb') as destination:
    shutil.copyfileobj(source, destination)
'@ | & $pythonExe - $archive $restored
& $pythonExe Tools/tests/analyze_performance.py $restored --warmup-frames 0 --output Saved/Acceptance/Reanalysis_Final20.json
```

复算前核对恢复 CSV 的 SHA-256 与 manifest 中该原始文件的 `sha256`，不要将 gzip 容器的 `artifact_sha256` 当作解压后文件的哈希。上述示例不会从统计中排除长帧。

## 图像语境

- `ScreenShot00010.png`：新正式测试的自然战斗截图，30 FPS 上限、第 2 场；请求截图时全局与玩家时间倍率均为 **1.0**，原生受击停顿仍启用。UE 在后续渲染帧保存图像；相关开销属于 30 FPS 测试，未混入本次 60 FPS CSV。
- `ScreenShot00011.png`：最终冷启动后的暂停试玩界面，双方满血、P继续；它是交付状态截图，不是性能样本。
- 旧 `VFX_*.png`：独立效果展示夹具，使用 **0.3 倍慢放**，用于观察命中、格挡、AOE、剑气与拖尾，不代表正常战斗节奏。
- `ScreenShot00008.png` / `ScreenShot00009.png`：靠墙镜头夹具，不是自然战斗截图；`ScreenShot00005.png` / `ScreenShot00006.png` 也是旧靠墙夹具。
- `ScreenShot00007.png`：旧 192140 批次的正常速度第 2 场截图，保留旧批次范围，不标作新主报告截图。
