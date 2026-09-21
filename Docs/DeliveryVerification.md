# 交付验收记录

当前Build14，Source `4542b8d`、Content/tests `3787b6c`、Config `027dc88`。当前配置正式20场已通过495/495，30/60fps各10场、17胜3败0超时（主动17胜2败、被动1败），cleanup_errors=null。默认链29项、扩展恢复21项及AI/空间专项通过；补充十场采样完成，保留独立覆盖失败。最终冷启动359/359通过，暂停试玩交接12/12通过。交付为编辑器PIE，不含独立可执行包。

## 20 场基线发现与修复

原始报告：`Saved/Acceptance/arena_acceptance_20260921T185232088295Z.json`。30/60 fps 各 10 场已完成，`status=failed`、`accepts_twenty_rounds=false`；唯一失败为 30 fps 第 10 场的 `fight.retry_position`。两场败局分别是30fps第1场主动策略自然落败，以及30fps第10场预设无攻击输入的被动死亡覆盖；60fps第10场仍为主动策略。没有超时，不能用18胜掩盖验收断言失败。

该场 R 重试后，玩家位置正确、双方生命/韧性/Idle/Montage/临时对象清理通过，但 Boss 从预期 `(600,0,106.15)` 变为 `(600,-60.0002,148.5292)`。事件记录显示 Boss 在重生点重新发动了 LeapRight，之后才被测试器停止；这是重试新树把整帧时间提前计入反应窗口的时序问题，不能通过放宽位置容差消除。

源码修复将 Select/Recover 与 Execute 看门狗按状态进入后的实际世界时间计算，保留原随机范围、权重、冷却和伤害；Reset/Die 另显式清除累计力、待执行 Launch 与输入。此轮具体偏移来自**重试后的新动作**，待执行 Launch 清理是独立补全，不应误称为此次根因。11版定向26项已通过，13版正式重验469项已全部通过；旧基线报告保留。

基线真实 CSV 已分析：`Saved/Profiling/CSV/Combat_1080pHigh_60_20260921T185232088295Z.csv`，22,071帧全部保留，FrameTime mean17.853ms、p9963.749ms、1%low9.573fps；详见 [Performance](Performance.md)。这是修复前基线，不能贴为13版成绩。

## 分项证据

| 项目 | 状态 | 实际证据 | 范围与限制 |
| --- | --- | --- | --- |
| 13版构建 / 资产重载 | PASS | Build13：6.93秒、4actions；`Build13_AssetValidation.json` success=true | 33BP、39Montage、216资产；不替代最终冷启动 |
| 11版重试/清力专项 | PASS（限定） | `Build11_Directed_20260921T191304332667Z.json`：26/26 | queued Launch清理与60/2fps真实R，孤立生命周期压力测试 |
| 13版组合技能专项 | PASS（限定） | `CombinedSources_20260921T192102267435Z.json`：17/17 | 固定windowID、独立projectile/AOE ID、serial回调重启保护；12版191815报告旧release重启迟伤18的失败保留 |
| Runtime + Editor 编译 | PASS | `Saved/Build_VFXCamera_09.log`：Result Succeeded，30.59 秒 | 仅证明该批 UBT 编译完成，不证明最终冷启动或玩法通过 |
| Ribbon Editor helper 增量编译 | PASS | `Saved/Build_Ribbon_10c.log`：Succeeded，7.79 秒；helper 提交 b480d8d，最终 Content/tools 检查点 3a322b1 | 不替代最终完整保存后的冷启动 |
| CLI 文件执行与持久 globals | PASS（限定） | `Saved/Acceptance/CLIFileProbe.json`、`CLIFilePersistence.json` 均 success=true | 实际 --file 中文空格路径、docstring 含 helper.py、正确 __name__/__file__ 断言及后续函数调用通过。终端 echo 中文乱码属显示问题，真实文件名断言通过 |
| 独立新标签技能示例 | PASS（21/21） | `SkillExtensionFinal_20260921T195256502504Z.json` | `SkillExtensionFinal_20260921T195256502504Z.json` 已通过21项：真实PCInputKey四标签扩展链累计130伤害，前三段为合法combo取消、末段正常结束；Tag从不可变字符串重建独立副本，保存并实际重载后确认Attack3.Next恢复Attack4且玩家CDO技能表恢复。`DefaultChainRepair_20260921T195055491298Z.json` 记录旧live wrapper引用污染的修复。旧 `SkillExtensionNewTagPIE.json` 的四链观察保留，但其同引用比较所得defaults_restored不构成恢复证明，现明确撤销。 |
| 最终冷启动 | PASS（359/359） | `FinalColdStart_20260921T204520545958Z.json` | 33BP、39Montage、216资产、地图/DLL/NextAttack4/Mass0只读核实；引擎13条自测失败另列，不宣称零error |
| 最终暂停试玩交接 | PASS（12/12） | `FinalHandoff_20260921T204548707031Z.json`；`ScreenShot00011.png` | 1080p High、HP300/1500、Idle、global1、Mass0/Tracefalse/Named0/GPUCSV0、全部键释放、无runner回调；中文暂停菜单实际接受，P继续 |
| 当前默认四连 | PASS（29/29） | `default_chain_only_20260921T195607760663Z.json` | 30/60fps真实PCInputKey四点击、4Tag、104伤害、结束/cleanup通过；不替代新20场 |
| Build14 / 默认链冷启动 | PASS（限定） | `Build_DefaultChain_14.log` 3.61秒3link actions；`DefaultChain_ColdStart.json` | 当前地图、Next与重链接DLL实际核实；Source4542b8d、Content/tests3787b6c |
| 前台实际音频输出 | PASS（限定） | `Saved/Acceptance/CombatNativeFocusedOutput.json` 与同名 WAV | 85.2053 秒、8 声道、48kHz，peak=.388458、RMS=.0074055、app_volume_bypass=0；实际非零输出，样本峰值低于满幅，无满幅削波。不是逐音效混音或听感全验收 |
| 原生 OS 鼠标与部分键位 | 已观察（限定） | `NativeInputSmoke_previous_20260921T184149746170Z.json`；协调者操作记录 | 第一轮 Attack1=2、Parry=1、控制器 yaw 变化54.2446°；协调者确认实际 LMB/RMB/mouse 与 P暂停/R重试。未验证人工全键位，见下文 |
| 13版独立空间 / 镜头场景 | PASS（限定） | `Saved/Acceptance/arena_spatial_visual_20260921T194122Z.json`：15/15；截图 `Saved/Screenshots/WindowsEditor/ScreenShot00008.png`、`ScreenShot00009.png` | 四墙地/空 Dash、相机回缩、仅玩家隐藏/离墙恢复、碰撞不变、Q 切换、直接 Montage 中断清理；不是自然对局或所有场景视觉证明 |
| 13版独立 AI 场景采样 | PASS（限定） | `arena_ai_scenarios_20260921T193914Z.json`：140次选招、701/701；`arena_ai_near_20260921T194032Z.json`：64配对、258/258 | 延迟选招、有效墙边夹具、注入半血阶段切换、近身配对；独立场景不替代自然20场 |
| 历史20场 / 当前配置重验 | 基线 FAIL；13版旧配置限定PASS；当前495/495 PASS | `arena_acceptance_20260921T192140351854Z.json`：status=passed、accepts_twenty_rounds=true、469/469 | 17胜3败0超时，主动17胜2败/被动1败；30/60各10，cleanup_errors=null。旧18/2基线 retry_position FAIL保留；13版无默认四标签exact验证，当前修复配置另以202025报告495/495通过 |
| 当前配置正式20场 | PASS | `arena_acceptance_20260921T202025583112Z.json`：495/495、accepts_twenty_rounds=true | 30/60各10；17胜3败0超时，主动17胜2败/被动1败，cleanup_errors=null；最终冷启动359/359通过，暂停试玩交接12/12通过，补充十场实测已完成 |
| 1080p High 性能 | 13版已实测 | `Performance_1080pHigh_60_20260921T192140351854Z.json`：22,910帧、warmup=0 | mean16.8093ms、p9919.6930ms、max122.4849ms、1%low33.7397fps；GPU p994.0681ms。全部长帧保留，不宣称稳定无卡顿60fps |
| 延后写盘补充性能 | 实测；覆盖 FAIL保留 | `runtime_profile_20260921T193559409889Z.json`：148/149，缺自然剑气覆盖 | 三场6377帧，p9916.701764ms、max48.4579ms、1%low48.7492fps；不替代正式20 |
| GC观测补充性能 | 149/149 PASS（限定） | `gc_profile_20260921T194436862733Z.json` 与 `GCAnalysis_20260921T194436862733Z.json` | 三场6219帧，p9916.71002ms、max63.6397ms、1%low46.1384fps。tick最大1.533ms、观测GC最大7.387ms，未找到主要长帧关联；未关闭GC |
| 最终十场延后写盘补充 | 实测；覆盖FAIL保留 | `runtime_profile_20260921T203637661555Z.json`：252/253，9胜1被动败0超时 | 唯一自然剑气覆盖失败；21060帧0剔除，p9916.7814/max25.8148ms、1%low56.9416fps；不替代正式20 |
| VFX 与近墙镜头可见性 | PASS（限定） | 协调者接受 `VFX_final_hit/parry/aoe/wave.png`、`VFX_final_warning.png`、`VFX_ribbonactive_player_ribbon.png`、`VFX_ribbonactive_boss_ribbon.png`、`ScreenShot00005.png` / `00006.png`；见证据快照 | 实际出手窗口冷/暖刀带可见；近墙只隐藏玩家、自影和 Boss 可见，离墙恢复。属于接受的画面与场景，不代表正式20场或性能通过 |
| VFX 交接运行状态 | PASS（限定） | `Saved/Acceptance/VFXHandoff.json`、`VFXFinalReloadedProperties.txt` | 无捕获回调、未暂停、timeDilation=1、1920×1080、双方满血300/1500、归属Niagara为0/0、AudioCvar=0；重载系统valid/ready。仅此交接时点 |
| 独立打包版 | 未交付 | 无 | 当前范围为编辑器 PIE |

## 最终交付结论

正式报告：`Saved/Acceptance/arena_acceptance_20260921T202025583112Z.json`，status=passed、accepts_twenty_rounds=true、495/495。历史469项旧配置和首轮retry_position失败仅保留各自证据，不替代此报告。

最终延后写盘十场 `runtime_profile_20260921T203637661555Z.json` 为252/253：9胜1被动败、0超时，唯一coverage.natural_projectile失败，原FAILED报告保留；它不替代正式495项通过，剑气已有正式与专项覆盖。对应 `Performance_Supplemental_1080pHigh_60_20260921T203637661555Z.json` 全部21,060帧、0剔除，mean16.6762ms、p9916.7814ms、max25.8148ms、1%low56.9416fps，>20ms共13帧、>33.3ms为0。预热及第10场被动策略不同，不能把差异全部归因JSON写盘，也不宣称稳定无卡顿60fps。

最终保存重开报告 `FinalColdStart_20260921T204520545958Z.json` 已通过359/359，核实33BP、39Montage、216资产、地图、DLL、NextAttack4及Mass0。最终暂停试玩交接 `FinalHandoff_20260921T204548707031Z.json` 已通过12/12，截图 `Saved/Screenshots/WindowsEditor/ScreenShot00011.png` 经协调者实际查看接受；窗口已激活，按P继续。引擎启动13条格式化自测错误归属及限制见 [EngineStartupNotes](EngineStartupNotes.md)，不宣称全日志零错误。完整性能分析与版本限制见 [Performance](Performance.md)。前台音频非零且无满幅削波的限定检查保持；旧失焦全零与其他失败记录不删除。

操作入口见 [README](../README.zh-CN.md)，正式执行说明见 [Testing](Testing.md)，统计定义见 [Performance](Performance.md)。历史诊断中的失败须保留，不应通过删除失败记录或混用不同版本数据得到最终 PASS。

`VFX_final_capture.json` 当前状态为 captured，标注 isolated skills 与 game dilation .3；这是慢放取证，不是正常速度的性能或对局验收。`VFXLifetime.json` 的 passed 是 45 个临时效果实例的寿命观察，不能据此把最终 VFX 视觉行改为 PASS。

## 保留证据与输入验证限制

最终证据包见 [Evidence/Final_20260922](Evidence/Final_20260922/README.md) 和 [SHA清单](Evidence/Final_20260922/manifest.json)：实际正式报告、冷启动/交接、图像、历史失败与无损压缩的完整CSV均保留。大体积WAV和原始trace记录本地路径及SHA，媒体本体仍在Saved，单独复制证据目录不包含这些引用文件。较早的 [PreFormal快照](Evidence/PreFormal_20260922/manifest.json) 保留历史范围。

当前 `NativeInputSmoke.json` 是第二轮极短键盘 tap 的未观察记录，不能标为 PASS，也不能用它抹掉第一轮已观察的鼠标事件。OS Space/W 短 tap 可能在同输入帧按下又松开：W 的按住状态回到 false，Space 可在 CharacterMovement 检查前已 StopJumping。Shift 的 Dash 未观察到，尚需工具扫描码/键保持时间/焦点与角色状态复核；没有证据表明默认 BindKey 的 modifier=false 会拒绝真实 Shift（UE 该条件表示不要求修饰键）。上述是工具验证边界，不宣称人工全键通过，也不把输入工具未观察等同于确定玩法缺陷。

历史输入 JSON 中的 `Human OS input` 标签并不精确：实际操作者为 root/sky 原生 Windows 输入自动化，不是真人试玩。原始 JSON 保持不改，本文和 manifest 明确更正其解释；不能据此宣称人工试玩或人工全键位验收。

UE PlayerController InputKey 的脚本检查覆盖情况以正式报告为准；首轮 20 场基线的失败已在上文列明，诊断单场和独立场景不能替代修复后的正式重验。13版旧配置20场及性能实测保留，不能证明当前默认链修复配置；新配置默认四连、扩展恢复和冷启动已通过，当前配置正式报告 `arena_acceptance_20260921T202025583112Z.json` 已通过：status=passed、accepts_twenty_rounds=true、495/495，30/60fps各10场，17胜3败0超时（主动17胜2败、被动1败），cleanup_errors=null。 最终冷启动359/359通过，暂停试玩交接12/12通过，补充十场实测已完成。

当前范围仅编辑器PIE。战斗音乐按现有ReplayMusic逻辑循环，AudioComponent设为UI音频，暂停时仍可播放；暂停不等于静音。补充十场唯一自然剑气覆盖FAIL及引擎启动13条自测失败均保留，不能以交付完成掩盖这些限定记录。
