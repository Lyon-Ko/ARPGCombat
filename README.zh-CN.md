# Combat · 剑斗演示工程

UE **5.8.2** 单人第三人称剑斗工程：玩家与 Boss、GAS 技能、Montage 通知、可扩展蓝图与技能数据。交付为**编辑器 PIE 工程**，不含独立打包版本。

正式30/60fps共20场 **495/495** 项通过；最终冷启动359项、暂停试玩交接12项通过，当前按 **P** 继续战斗。默认四连、独立技能扩展及AI/空间专项已有验证。真实性能、补充覆盖失败和引擎启动自测限制见 [交付记录](Docs/DeliveryVerification.md)、[性能报告](Docs/Performance.md) 与 [启动说明](Docs/EngineStartupNotes.md)。

## 打开试玩

1. 用 UE 5.8.2 打开根目录 `Combat.uproject`。
2. 默认地图为 `/Game/Combat/Maps/L_CombatArena`，默认模式为 `BP_CombatGameMode`；若恢复旧会话，手动打开竞技场。
3. 点击 **Play**，再点击游戏视口获取键鼠输入。`Esc` 结束 PIE，`Shift+F1` 释放鼠标。

| 操作 | 按键 |
| --- | --- |
| 移动 / 自由镜头 | WASD / 鼠标 |
| 剑击、连段、状态派生 | 左键逐次点击 |
| 空中下劈 | 空中长按左键 |
| 精准格挡 / 成功后反击 | 右键 / 提示期间左键 |
| 八方向短冲 / 无方向后撤 | 左 Shift |
| 跳跃 / 二段跳 | 空格 / 再按空格 |
| 锁定或解除目标 | Q |
| 暂停、音量/灵敏度/震动设置、继续 | P |
| 胜负后再战 | R |

详细时机和限制见 [玩家指南](Docs/PlayerGuide.zh-CN.md)。角色为原生 Kwang / Greystone；资源来源、授权与原创资源说明见 [Assets 来源清单](Docs/Assets/ASSET_SOURCES.md)。

## 工程和扩展入口

- `Source/Combat`：角色、GAS、技能积木、StateTree AI、UMG、命中与表现生命周期。
- `Source/CombatEditor`、`Tools/editor`：可编辑蓝图图表、动画和资产生成工具。
- `/Game/Combat/Abilities`、`Skills`、`Animations/Native`：GA 蓝图、技能 DataAsset、最终原生 Montage/动画蓝图。
- [技能扩展指南](Docs/SkillExtension.zh-CN.md)：通过 Gameplay Tag、GA 蓝图、Montage 通知、DataAsset 与 GameplayEffect 配置新技能；包括连段、查询、优先级和 Buff 清理作用域。
- [运行时接入契约](Docs/RuntimeIntegration.md)、[架构](Docs/Architecture.md)、[测试说明](Docs/Testing.md)、[性能采样](Docs/Performance.md)。

生成 pipeline 会覆盖基础资产。自定义资源请复制到独立 `Custom` 路径，不要把基础资源上的手改误当作可重复生成的结果。

## PowerShell 工具

在工程根目录执行；默认引擎路径是 `D:\UE5.8\UE_5.8`，可传 `-Engine` 覆盖。

```powershell
.\Tools\Combat.ps1 doctor
.\Tools\Combat.ps1 build
.\Tools\Combat.ps1 editor
.\Tools\Combat.ps1 python -Code "import unreal; print(unreal.SystemLibrary.get_engine_version())"
```

完整 build 前先保存并正常关闭 UE；doctor 会检查本地工具及项目匹配的编辑器 remote 连通性，编辑器未运行时 remote 检查不会通过。python 入口需要匹配本工程的编辑器已运行；它执行实际编辑器代码。

正式验收是 **opt-in**，不会因打开工程或导入脚本自动启动。在批准的、未暂停的 PIE 中，由唯一测试执行者运行：

```python
import runpy
acceptance = runpy.run_path(r'D:\UEproject\Combat\Tools\tests\start_acceptance.py')
acceptance['start']()
# 后续单独查询或停止，等待时让 Slate 正常 tick：
acceptance['status']()
acceptance['stop']()
```

入口安排 30/60 档各 10 场，并在 60 档采集 UE CSV。禁止与其他测试 runner 同时启动；结果写入 `Saved/Acceptance`、CSV 写入 `Saved/Profiling/CSV`。**运行请求不等于通过**，最终报告路径、结果与限制由交付验收记录汇总。
