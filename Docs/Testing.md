# Combat 测试入口与证据

当前 Source `4542b8d` 未改，Content+tests `3787b6c`、项目Config `027dc88`（mass.FullyParallel=0），Build14 重链接 PASS（`Build_DefaultChain_14.log`，3.61秒、3个link actions）。`DefaultChain_ColdStart.json` 已核实实际默认地图、Next标签和当前DLL；当前配置正式报告 `arena_acceptance_20260921T202025583112Z.json` 已通过：status=passed、accepts_twenty_rounds=true、495/495，30/60fps各10场，17胜3败0超时（主动17胜2败、被动1败），cleanup_errors=null。 最终冷启动359/359通过，暂停试玩交接12/12通过，补充十场实测已完成，已完成本次编辑器PIE交付。 `default_chain_only_20260921T195607760663Z.json` 已通过29/29：30/60fps真实PCInputKey四点击，精确Attack1→Attack2→Attack3→Attack4、累计104伤害、对应结束和cleanup均通过。 旧 `arena_acceptance_20260921T192140351854Z.json` 的469/469、17胜3败0超时是旧配置限定证据；该自然bot无默认四标签exact断言，不能作为新配置最终20场结论。

## 正式 20 场入口

使用已有的、未暂停的 1920×1080 浮动 PIE，由当前唯一测试执行者调用。导入脚本不启动 UE/PIE，也不自动开始测试。

```python
import runpy
acceptance = runpy.run_path(r'D:\UEproject\Combat\Tools\tests\start_acceptance.py')
acceptance['start']()
# 在后续独立调用中查询或停止；不要用循环阻塞 Slate：
acceptance['status']()
acceptance['stop']()
```

入口拒绝已运行的正式/独立 runner。不要同时使用 UI 自动化、其他 remote 脚本或手动输入控制角色。测试按 30fps 10 场、60fps 10 场运行现有输入、防御、生命周期专项和自然对局。源码条件为 `self.fps == self.caps[0] and number == self.rounds`，因此正式入口只有30fps第10场预设为不攻击的自然死亡覆盖，60fps第10场仍使用主动反应式策略；其余场次均主动。机器人不会注入伤害、改变血量或强行宣布胜负；失败/超时与诊断证据保留。

实际视口通过 PlayerController 回读；画质设为 High（sg*=2）、sg.ResolutionQuality/ScreenPercentage=100、VSync=0、PoolSize=2048、MotionBlurQuality=0 并检查实际值。报告记录引擎版本、运行 DLL 时间/大小/SHA-256、CVar 原值/回读和运行日志中的 RHI/显卡/驱动信息。文件名为微秒 UTC 的 `Saved/Acceptance/arena_acceptance_*.json`，不覆盖历史报告。

30fps第2场正常自然战斗会请求UE `Shot SHOWUI`，记录时间、倍率、视口和新截图路径，截图开销保留在30档。60档第1场前设置CSV文件名并单独START，第10场及重试完成后STOP，等待实际写出。CSV包含自然对局、reset、回调、证据保存和所有长帧；`--warmup-frames 0` 分析。性能定义及实测见 [Performance](Performance.md)。延后写盘补充支持3–10场，详见 [RuntimeProfile](RuntimeProfile.md)，独立于正式20场。

报告的 `status=passed`、`accepts_twenty_rounds=true`、恰好20场及全部断言应共同核对。已完成多少场、胜场数或中间0失败都不能替代最终状态。手动 stop 必须保留 stopped；游戏超时不能通过重置转成胜利。

## 验证范围与边界

- **脚本输入**：通过项目 PIE-only PlayerController InputKey 接口提交真实按下/松开，再观察技能、移动、跳跃。包括跑动空中前/反向 Dash、暂停松键残留等。InputKey 返回 handled 不等于游戏效果成功，判定以实际状态为准。
- **注入专项**：前后格挡、死亡/阶段阈值等部分夹具用公开 ReceiveCombatHit 或显式位置设置，明确记录为 isolated/synthetic；不计为自然伤害或自然击杀。
- **自然对局**：真实StateTree与公开玩家输入交互，保留胜败/超时、命中/格挡、阶段和重试证据。正式20仅30fps第10场预设被动。RuntimeProfile只有60fps一个档位，其所选最后一场被动；默认3场为第3场，最终10场采样为第10场。
- **OS 输入**：历史 NativeInputSmoke 的 Human 标签实际指 root/sky 原生 Windows 输入自动化，并非真人试玩。第一轮观察到 Attack1两次、Parry一次、yaw54.2446°，P/R由协调者观察；第二轮短tap未观察到Space/W/Shift效果，不能标为人工全键PASS。InputKey脚本与OS扫描码/焦点/短tap是不同验证层。
- **视觉/声音**：孤立慢放VFX截图、前台非零录音及独立镜头测试只证明各自范围，不替代正常速度自然对局与性能。来源和哈希见 [DeliveryVerification](DeliveryVerification.md)。

## 独立专项入口

以下脚本都采用 Slate 非阻塞生成器和 start/status/stop，要求现有 PIE、互斥运行；完整用法以各文件公开函数为准，不调用私有 AI 选招函数。

| 脚本 | 目的与限制 |
| --- | --- |
| `Tools/tests/arena_ai_scenarios.py` | 配对seed观察真实Attack/Parry/Dash后的StateTree选招；墙边扫掠夹具；AOE期间显式半血注入。分布不保证精确概率比例。 |
| `Tools/tests/arena_spatial_visual.py` | 四墙地/空Dash、春臂回缩、仅本地玩家近镜头隐藏与恢复、碰撞不变、Q切换、直接Montage停止清理。已知矩形竞技场边界夹具。 |
| `Tools/tests/arena_regression.py` | 原有专项/自然bot基础类；单场诊断不得冒充正式20入口。 |

实际属性通过本地UE PythonStub及Runtime头文件核实，例如 `get_editor_property('character_movement')`、委托 add_callable/remove_callable、WorldTime、AnimInstance montage_stop。每轮异常须保留完整错误，不凭AST通过宣称反射或PIE通过。

## 历史证据与修复链

所有下列 JSON 位于 `Saved/Acceptance`，失败报告继续保留。

| 报告 | 已记录结果 | 解释 |
| --- | --- | --- |
| `arena_regression_20260921T180318Z.json` | 单场诊断发现AOE取消无效 | 原取消API比较CDO却传instance，后改为SpecHandle。不是20场报告。 |
| `arena_acceptance_20260921T185232088295Z.json` | 20场18胜2败0超时；469断言仅30档第10场retry_position失败 | 新树把重置前整帧时间计入reaction，R后新LeapRight造成偏移，整体failed；未放宽容差。 |
| `Build11_Directed_20260921T191304332667Z.json` | 26/26 PASS | queued Launch后Reset/死亡清力、60fps及2fps真实R。粗帧输入步约.4秒，新AI技能约复活观察后1.2秒出现；孤立压力测试。 |
| `CombinedSources_20260921T191815227899Z.json` | 16/17；旧AreaRelease回调取消后同技能重启仍造成18伤害 | 12版失败证据保留，不能用其他ID用例通过掩盖。 |
| `CombinedSources_20260921T192102267435Z.json` | 13版17/17 PASS | 固定近战窗口ID、独立projectile/AOE ID、同窗口去重、回调取消同实例重启隔离。实际投射物/扫掠；为观察临时改Duration/Cooldown，finally恢复，不保存Content，Damage18不改。 |
| `arena_spatial_final_vfx09.json` | 15/15 PASS | 独立墙边/镜头/直接Montage中断，非自然对局。 |
| `arena_ai_scenarios_20260921T181713Z.json` / `arena_ai_near_20260921T182044Z.json` | 701 / 258断言PASS | 独立观察、墙边、半血和近身配对，不等于完整最终版本重验。 |

最终13版独立重验：`arena_ai_scenarios_20260921T193914Z.json` 140次实际选招、701/701；`arena_ai_near_20260921T194032Z.json` 64配对、258/258；`arena_spatial_visual_20260921T194122Z.json` 15/15，截图00008/00009。均通过，保持上述独立夹具边界；历史报告仍保留。

首轮CSV真实保留22,071帧、warmup0，FrameTime mean17.853ms/p9963.749ms/max755.307ms/1%low9.573fps。不能宣称稳定60fps。`PersistenceBenchmark_20260921_baseline.json`离线9次比较得indent2总耗时中位80.743ms、compact19.456ms；随后接入orjson3.12.0并保留所有字段/历史/同步保存频率，缺依赖明确stdlib fallback。`SerializerUE_20260921T191227144319Z.json`记录真实UE完整save17.181ms；裸编码器基准不是完整路径成本，也不能将全部长帧归因于JSON。有限数验证拒绝NaN/Inf，固定大小persistence_timing记录既往保存开销。

## 当前验证结论

当前正式 `arena_acceptance_20260921T202025583112Z.json` 已通过495/495、17胜3败0超时。默认四连、扩展恢复及AI/空间独立证据见上文；历史失败不删除。

最终延后写盘十场 `runtime_profile_20260921T203637661555Z.json` 为252/253：9胜1被动败、0超时，唯一coverage.natural_projectile失败，原FAILED报告保留；它不替代正式495项通过，剑气已有正式与专项覆盖。对应 `Performance_Supplemental_1080pHigh_60_20260921T203637661555Z.json` 全部21,060帧、0剔除，mean16.6762ms、p9916.7814ms、max25.8148ms、1%low56.9416fps，>20ms共13帧、>33.3ms为0。预热及第10场被动策略不同，不能把差异全部归因JSON写盘，也不宣称稳定无卡顿60fps。

最终只读冷启动 `FinalColdStart_20260921T204520545958Z.json` 为359/359通过；最终 `FinalHandoff_20260921T204548707031Z.json` 暂停试玩交接12/12通过，截图00011已实际接受；补充采样和正式测试是不同验证范围，不能将补充覆盖失败改成PASS，也不能用它抹掉正式与专项已有的剑气覆盖。见 [DeliveryVerification](DeliveryVerification.md)。

## 最终版本新标签四连段复验（独立 opt-in）

`Tools/editor/verify_skill_extension_final.py` 仅加载定义；确认其他 runner 停止且无 PIE，加载后显式 `start()`，用 `status()` 查询、`stop()` 中止。其调用会临时编译保存玩家技能表和 Attack3.NextSkillTag，结束 PIE 后恢复原值、编译保存并实际 reload_packages 读回验证。若相关包有未保存改动会在变更前拒绝，请先自行保存；运行期间不要编辑这两个资产。脚本不会启动或替代正式20场。

真实 PlayerController InputKey 连段必须精确产生 Attack1→Attack2→Attack3→Combat.Skill.Example.CrescentBurst 四次开始与对应结束（前三段为合法连段取消，末段正常结束）、总伤害130，否则（包括超时）严格失败。Boss AI仅在该孤立夹具停止；不改数值。结果是唯一UTC的 `Saved/Acceptance/SkillExtensionFinal_*.json`，包含当前DLL SHA-256和默认配置重载读回，不覆盖历史 `SkillExtensionNewTagPIE.json`。异常或手动停止同样松开LMB、移除委托、请求结束PIE并恢复资产；恢复失败会显式记录 RESTORE FAILED，不能标通过。首次报告 `SkillExtensionFinal_20260921T194848720875Z.json` 的错误结束语义FAIL保留。`SkillExtensionFinal_20260921T195256502504Z.json` 已通过21项：真实PCInputKey四标签扩展链累计130伤害，前三段为合法combo取消、末段正常结束；Tag从不可变字符串重建独立副本，保存并实际重载后确认Attack3.Next恢复Attack4且玩家CDO技能表恢复。`DefaultChainRepair_20260921T195055491298Z.json` 记录旧live wrapper引用污染的修复。旧 `SkillExtensionNewTagPIE.json` 的四链观察保留，但其同引用比较所得defaults_restored不构成恢复证明，现明确撤销。 `default_chain_only_20260921T195607760663Z.json` 已通过29/29：30/60fps真实PCInputKey四点击，精确Attack1→Attack2→Attack3→Attack4、累计104伤害、对应结束和cleanup均通过。
