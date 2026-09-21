# Arena 回归测试

## 当前状态与权限

`Tools/tests/arena_regression.py` 已准备好做本地 AST 与公开接口核对。**本次没有执行 remote、没有启动 PIE，也没有产生通过记录。** 它独立于 `Tools/editor/probe_pie_skills.py` 的 19 招冒烟矩阵，不重复宣称技能逐一验收。

必须由 Root / 编辑器负责人明确授权后，在当前工程的实际 PIE 世界执行。脚本导入只定义入口；不会自动开始 PIE、加载地图、改资产或修改 Source。执行会重置当前战斗、暂时改变 `t.MaxFPS`、使用玩家输入方法、移动角色，并在独立判定/生命周期用例中注入命中。不要与人工操作、另一个机器人或其他 PIE 探针同时运行。

## 运行

1. 编译并打开 `L_CombatArena`，等待 shader / Blueprint 编译完成。
2. 在编辑器负责人授权下启动单人 PIE，确认只有一个玩家与一个 Boss，均为真实 `CombatCharacter`，Boss 使用 `CombatAIController` 与实际 StateTree。默认核对玩家 Skeleton 源于 `/ParagonKwang/`、Boss Skeleton 源于 `/ParagonGreystone/`；允许 `/Game/Combat` 下新增武器 socket 的复制 Mesh，网格与 Skeleton 路径均写入报告。需已编译仅 PIE 有效的 `CombatEditorLibrary.InjectPlayerKey`。
3. 在获准的 UE Python 执行上下文调用：

```python
import runpy
arena = runpy.run_path(r'D:/UEproject/Combat/Tools/tests/arena_regression.py')
print(arena['start']())
```

默认在 30 fps 下做 10 场、60 fps 下做 10 场，共 20 场自然战斗。每场默认 180 秒世界时间上限；最坏情况约一小时，不能因运行时间长把超时当成胜利。可在授权后用 `start(fps_caps=(30,), fights_per_cap=1, fight_timeout=180)` 做调试，但这种运行不会满足完整 20 场验收。

脚本使用 `unreal.register_slate_post_tick_callback`。每次回调最多推进一个生成器步骤；等待世界时间时立即 `yield`，没有 `sleep`、忙等循环或阻塞远程调用。活跃对象保存在 `builtins._combat_arena_regression`，不依赖 `runpy` 的临时名字。

另一次获准的 remote / Python 上下文可以读取状态：

```python
import runpy
print(runpy.run_path(r'D:/UEproject/Combat/Tools/tests/arena_regression.py')['status']())
```

停止测试：

```python
print(runpy.run_path(r'D:/UEproject/Combat/Tools/tests/arena_regression.py')['stop']())
```

`stop` 记录 `stopped`，不会记为通过。结束时解除 Python 事件绑定、注销 Slate 回调、通过生成器 `finally` 和 cleanup 释放所有注入并保持的按键、释放攻击保持状态，并恢复原来的暂停状态、帧率上限与 AI 随机种子。脚本不会关闭 PIE。错误或 PIE 提前结束会写入失败和 traceback；恢复失败也记录在 `cleanup_errors`。

## 真实输入专项

新增专项已实现，尚未执行：

- W 跑动取得大于 100 cm/s 的前向速度 → Space 升空 → 保持 W 或切换 S → Shift。用实际 `OnSkillStarted/Ended` 位置差测量 Dash 的水平总位移，不包含 Dash 前惯性；目标 250 cm、距离容差 `25 + 650 / fps` cm、方向容差 12°，记录开始速度与技能时长。
- 空中保持 LMB / Space → P 暂停 → 释放 LMB / Space → P 恢复。通过真实技能事件要求启动 Air1 而没有残留 Plunge；在合法 Air1 恢复后再次 Space 必须成为第二跳，第三次仍不得增加计数。若过早落地或前置攻击未启动则失败，不能以空事件证明成功。
- Q 按下两次，通过公开 `is_target_locked()` 分别验证翻转与恢复；这是状态验收，HUD 文字视觉检查仍由编辑器负责人另行完成。

这些项目保留 finally/stop 按键释放及暂停恢复，需下一构建包含 `IsTargetLocked` getter，导入脚本不会执行测试。

每个帧率阶段首先运行 `input_cases`，使用编辑器仅 PIE seam → `FInputKeyEventArgs::CreateSimulated` → `PlayerController.InputKey`，不会调用私有输入函数。

- 八向短冲：W、WD、D、SD、S、SA、A、WA，固定控制视角且解除锁定。按 Shift 后跨帧观察 Dash 激活，并测量水平轨迹；目标 250 cm，距离容差 `35 + 650 / fps` cm、角度容差 12°。保持键在 `finally` 释放。场地阻挡造成轨迹不达标也记失败。
- 双跳：Space 按下/释放后跨游戏帧再按，要求跳跃计数 1→2、第二跳向上速度、第三次不增加次数、落地归零。没有直接改变速度或瞬移到空中。
- 暂停：P 按下后要求世界暂停；用非阻塞墙钟观察 0.25 秒，世界时间变化必须小于 0.001 秒；再次 P 恢复并要求世界时间推进。
- 生命周期和自然胜负后的重试均注入 R，等待实际输入处理后核对复活和残留。前者仍是明确标记的注入死亡用例。

输入 seam 返回的是 `InputKey` 的 handled 值；WASD 在角色 Tick 轮询，false 不等于没有更新保持状态。报告保留该值，是否有效由真实移动/技能断言判断。每次按键后让出 Slate 回调，不把提交按键的时刻当成技能开始时间。精准格挡计时读取角色公开 `GetSkillElapsedTime`。

## 判定与生命周期用例

这些用例使用实际配置的角色、实际 Parry GAS 激活和公开 `ReceiveCombatHit(FCombatHit)`，但**命中本身由测试注入**，结果存入 `standalone_injected_cases`，不混入自然战斗统计。

| 用例 | 公开路径与断言 |
| --- | --- |
| 正面窗口内 | `ParryPressed` 后约 0.10 秒注入命中：要求 `Parried`，生命不变 |
| 正面窗口尾段 | 约 0.15 秒命中，同样要求 `Parried`；实际到达不能超过 0.20 秒 |
| 正面窗口外 | 约 0.24 秒命中：要求 `Damaged`，按注入伤害扣血 |
| 背面窗口内 | 攻击者放到背后，约 0.10 秒命中：要求 `Damaged` |
| 交错去重 | 同一来源依次送入 old、old、new、old ID：要求 Damaged、Miss、Damaged、Miss，合计仅扣两次血 |
| 取消清理 | 激活真实 Boss AOE；通过公开组合块创建预警/弹体，取消后等待 1.5 秒，要求无迟到伤害、无技能/格挡状态、无所属弹体或新增附着组件 |
| 死亡清理 | 独立重置 fixture 后再次激活 AOE、创建弹体，注入明确标记的致死命中；要求 Killed、死亡与临时状态清理 |
| 重试 | 通过真实 R 键触发 `RetryEncounter`，要求双方复活、满生命/韧性、阶段清零、时间缩放恢复与临时对象清理 |

生命周期测试里使用 `ShowAreaWarning` / `EmitSkillProjectile` 是为了覆盖取消与死亡时确实存在临时对象的路径。报告记录注入和预条件；未成功创建弹体会失败，不会通过一个空场景“证明”清理成功。它不代替自然攻击的武器扫掠命中验证。

这里只断言可公开观测的状态，不读取私有 `bHitWindow`、命中列表或内部计时器，也不复制私有算法来产生预期答案。

## 20 场自然移动战斗

每场重置后启动真实 Boss StateTree，玩家机器人通过继承的 `AddMovementInput` 接近敌人，并调用 `AttackPressed` / `AttackReleased`、`ParryPressed`、`DashPressed`。防守决策在观察 Boss 当前技能后至少等待 0.24 秒，每次技能启动最多提交一次防御。AOE 先观察长蓄力，再响应真实 `Combat.Cue.AreaRelease` 闪光：闪光后至少 0.055 秒格挡，目标是在原始 0.18 秒延迟伤害前进入 0.20 秒窗口。闪光响应不重新附加 0.24 秒识别延迟。DashSlash 延迟到技能约 0.42 秒防守；普通近战保留 0.24 秒观察约束，快速首击可能先命中，这是策略限制而非游戏通过证据。报告记录实际观察时长、闪光反应时长与防守请求后的技能，不读取敌人原始输入，也不直接调用 Boss 招式决定下一步。

普通续段基于实际 `OnSkillStarted` 序号，每段只在约 0.36 秒提交一次；当前原生动作 ComboOpen 为 0.305–0.335 秒。避免固定频率反复覆盖 0.18 秒缓冲。格挡/冲刺后 0.32 秒不提交攻击，AOE 识别后至闪光后 0.28 秒保留防守，不用攻击取消格挡。攻击按住约 0.055 秒后释放，防止误触空中长按派生。该策略时序需随正式动作数据变更重新核对。

自然战斗期间不调用 `ReceiveCombatHit`，不修改双方生命/伤害、AI 恢复间隔、全局时间缩放或技能时长，也不瞬移取胜。任一方自然死亡才有 `victory` / `defeat`；超时保留 `timeout` 并失败，之后的重置仅用于清理。胜负后通过真实 R 键触发 `RetryEncounter` 再战，检查状态和出生点恢复。

每局持续记录：

- 世界/墙钟时长、输入次数、实际 `OnSkillStarted/Ended`、`OnCombatFeedback` 和 `OnCombatDeath` 事件。
- 命中与格挡 cue 次数、各角色实际技能启动计数、AI `ActionsExecuted`、第二阶段观察值、实际移动距离。
- 世界中的 `CombatProjectile` 数量、角色所属弹体峰值，以及角色拥有/附着组件相对初始基线的新增路径。
- 结果、重试后的残留、每条断言和每局是否通过。

20 场整体还要求至少一场自然 victory、一场自然 defeat，并至少观察到一次自然格挡、一次自然弹体与第二阶段。全部 defeat 不能通过，也不能宣称 Boss 可击杀。汇总分别记录胜利/失败/超时次数、自然败率、超时率与场次断言失败率。缺少这些会标记**覆盖不足导致失败**，不能单凭一批容易结束的战斗宣布完整通过。机器人表现不佳造成覆盖不足时，应先复核日志，再调整测试策略；不能补注入伤害或强设阶段来冒充自然覆盖。

## 时间与容差

使用世界时间判断技能窗口，并同时记录墙钟时间防止暂停/卡住后无限等待。命中调度允许 `1.5 / fps + 0.005` 秒的回调延迟，但窗口内用例的实际命中仍必须不晚于 0.20 秒；越界是调度失败，不允许扩大游戏格挡窗口来通过。

每个帧率阶段记录实际世界时间步长的中位数、p95、最大值和样本量；中位推算 fps 需与请求值相差不超过 15%，且至少采样 100 次。`t.MaxFPS` 只是上限，机器跑不到目标时会失败，报告不能被称为有效 30/60 fps 一致性结果。shader 卡顿或后台编辑器节流可能导致此项失败；修复环境后重新完整运行，保留旧失败报告。

## 结果文件与本地核对

输出为 `Saved/Acceptance/arena_regression_<UTC>.json`，最多约每秒原子更新一次，断言和场次切换时也立即落盘。另一次 status / remote 或直接只读此 JSON 即可查看进展。状态为 `starting / running / passed / failed / stopped`；只有完成全部断言且至少 20 场时，`accepts_twenty_rounds` 才能为 true。

移动组件使用已核实的 `get_editor_property("character_movement")`；不依赖未暴露的 `get_character_movement()`。输入 seam 已按本地头文件和实现检查，双跳计数按 UE `Character.h` 的 BlueprintReadOnly 属性核对。接口已按当前 `CombatCharacter.h`、`CombatTypes.h`、`CombatAIController.h` 与 `Docs/RuntimeIntegration.md` 核对。Python 委托 `add_callable/remove_callable`、`GetSkinnedAsset`、`GetChildrenComponents`、`GetTimeSeconds` 和控制台变量查询按本地 UE 5.8 源码核对。Python AST 检查可在不加载 UE 的情况下运行：

```powershell
& 'D:\blender\5.1\python\bin\python.exe' -c "import ast; from pathlib import Path; p=Path(r'D:\UEproject\Combat\Tools\tests\arena_regression.py'); ast.parse(p.read_text(encoding='utf-8')); print('AST OK')"
```

AST 和头文件核对不等于 UE 反射绑定或实际 PIE 通过。首次授权运行应先检查是否有 Python 名称/反射错误；任何错误保留为失败记录，修复后重新运行。
