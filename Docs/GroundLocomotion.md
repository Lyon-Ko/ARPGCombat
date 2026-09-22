# 地面 Locomotion 实时调参

Kwang 非锁定折返现使用官方动作重定向并融合持剑上半身的新片段，详见 [FreeSwordPivot.md](FreeSwordPivot.md)。其转向跟随 `PivotYaw` 曲线，下面的 TurnRate/TurnDelay 说明仅适用于旧动作路径；刹车、反向加速参数仍然生效。

现在直接编辑 **`/Game/Combat/Config/DA_Locomotion`** 原生 Data Asset 的 **Details**。完整参数、单位、默认值与范围见 [LocomotionParameters.md](LocomotionParameters.md)。

1. 打开竞技场 PIE，WASD 移动，快速切换相反方向触发 Pivot；Q 切换锁定。
2. 在内容浏览器打开 `Combat/Config/DA_Locomotion`，在 Details 中展开 Movement、Pivot 等分类修改数值，约 0.2 秒后自动生效，无需保存、重开 PIE 或编译。结束 PIE 后 Ctrl+S 保存资产，数值会在下次打开项目时保留。
3. 画面左上角显示 `Locomotion r版本 | Speed | InputA | BrakeA | Brake/Reverse/Move | Pivot进度`。InputA 为输入加速度，BrakeA 为折返减速度；刹车时 InputA 为 0 是正常的。
4. Details 提供范围限制与中文提示。字段关系错误（例如 JogSpeed 大于 FastSpeed）会显示错误并保留上次有效配置；修正后自动恢复。
5. 控制台命令 `Combat.Locomotion.Reload` 可立即重新应用资产。Debug 分类中的 Overlay 关闭持续显示。
6. **Debug → MovementVectors** 开启世界空间移动箭头，与文字 Overlay 开关独立。绿色表示普通移动目标，黄色表示 Pivot 刹车时的目标，紫色表示反向加速目标，橙色表示技能位移方向；蓝色表示 CharacterMovement 的水平速度，长度随速度缩放。刹车时可看到目标箭头与蓝色速度箭头相反。零向量不画箭头，关闭后下一绘制帧清除；不影响移动逻辑。
7. 同分类的 MovementVectorLength / MovementVectorHeight 调整箭头长度和离胶囊底部高度，支持 PIE 实时修改。此可视化用于编辑器/开发构建。

## 建议先调的项目

| 目的 | 配置键 | 当前默认 |
|---|---|---:|
| 刹车更慢、保留惯性 | Pivot.BrakingDeceleration | 900 cm/s² |
| 刹车附加阻力 | Pivot.BrakingFriction | 0 |
| 反向起步快慢 | Pivot.ReverseAcceleration | 1200 cm/s² |
| 折返转身快慢 | Pivot.TurnRate | 900°/s |
| 开始转向的延迟 | Pivot.TurnDelay | 0.02 s |
| 反向起步最早时间 | Pivot.ReverseDelay | 0.1 s |
| 反向起步动画进度门槛 | Pivot.ReverseMinProgress | 0 |
| 反向起步朝向误差门槛 | Pivot.ReverseMaxFacingAngle | 45° |
| 普通移动加速 | Movement.Acceleration | 1600 cm/s² |
| 普通松键减速 | Movement.BrakingDeceleration | 1200 cm/s² |
| 普通转向 | Movement.TurnRate | 900°/s |
| 四向速度 | Movement.ForwardSpeed/BackwardSpeed/LeftSpeed/RightSpeed | 560 cm/s |
| 地面动画原速 | Animation.PlayRate | 1 |
| Pivot 动画原速 | Pivot.PlayRate | 1 |

Pivot 已改为独立的刹车与反向加速阶段。刹车减速不再依赖普通地面摩擦，也不直接清零速度。
默认无额外摩擦，从 560 cm/s 以 900 cm/s² 减速约需 0.62 秒。低于 StopSpeed，且满足
ReverseDelay、ReverseMinProgress 和朝向条件后，开始逐步反向加速。

转向与整段动画长度解耦。默认 900°/s，180° 转身约 0.2 秒，另加 TurnDelay。
动画片段完整保留，播放倍率 1；反向加速可在动画仍然播放时进行。
若想更早回到循环移动，可开启 EarlyExitEnabled，并调整 ExitMinProgress、ExitMinSpeed。

## 生效范围与资产

Data Asset 是玩家运行时数值的唯一入口，会覆盖角色/动画蓝图上同类数值；Boss 保留既有行为。
`BP_CombatPlayer → Class Defaults → Locomotion → Locomotion Config` 已绑定此资产。此硬引用也保证配置随角色一起烘焙。
旧 INI 的 87 项现有数值只在首次创建资产时迁移；核对并保存成功后归档到 `Saved/LocomotionMigration/`，运行时不再读取 INI。
四向最高速度按角色局部方向区分，斜向采用椭圆限速，不叠加速度。

玩家动画蓝图：`/Game/Combat/Animations/Native/Kwang/ABP_CombatKwang2D`。
四个 `AM_Pivot_*` 和 `BS_Locomotion2D` 保留完整原速素材。
Pivot 使用每个角色自己的运行时蒙太奇副本，实时调融合和倍率不会改写源资产。
Animation.JogSpeed/FastSpeed 将真实速度映射到原 Blend Space 采样坐标，原采样点不被运行时修改。

技能可立即打断 Pivot；起跳、松键、改向和锁定切换也按配置退出。没有临时修改后遗漏恢复的全局加速度锁。
技能之间继续遵守原有取消窗口与连招输入缓存；资产可控制输入缓存、移动取消总开关与融合时间。
技能伤害、命中窗口、片段引用、Grounded/Airborne 图内过渡等仍在各自资产中编辑。

## 维护与验证

- 参数定义及合法范围：`Source/Combat/Public/CombatLocomotionParameters.inl`。
- `Tools/editor/generate_locomotion_config.py` 从参数定义生成带 EditAnywhere 属性的 Data Asset 类头文件和完整说明，不修改资产数值。
- `Tools/editor/configure_locomotion_asset.py` 首次创建并迁移资产、绑定玩家蓝图；再次运行保留已有资产调参值。
- `Tools/tests/ground_locomotion_regression.py` 验证完整动画、逐步刹车/加速、快速转向与技能衔接。
- `Tools/tests/locomotion_live_config_regression.py` 通过与 Details 相同的属性编辑接口，验证未保存资产修改、动作中修改参数和非法配置回退；退出时恢复测试前配置，若发现外部改动则保留外部改动。
- 报告写入 `Saved/Acceptance/GroundLocomotion.json` 和 `Saved/Acceptance/LocomotionLiveConfig.json`。

热更新检查覆盖四向限速、动画倍率与阈值、相机、同一次 Pivot 中的刹车/转向/反向加速与倍率修改、禁用 Pivot、无效值和字段关系回退。

Data Asset 迁移验证：87 项旧值逐项核对并保存；Development Editor 编译通过；资产绑定和未保存属性热更新检查 24/24 通过。测试结束后已恢复原值。
