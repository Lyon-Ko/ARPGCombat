# Kwang 非锁定持剑折返

2026-09-23 肘部修正：左折返约 0.80–0.85 秒曾因末端 IK 目标过远而接近完全伸直。左侧校准现采用平滑伸展限制，满权重时最大到肩腕可达长度的 90%，限制边界采用连续斜率过渡；右片段不变。尾段淡出区域刀尖与目标跑步姿态偏差约 0.11 cm。`sword_pivot_assets.py` 增加 0.75 秒后双臂接近锁直的回归检查。

已将 Epic Game Animation Sample UE 5.8 的左右跑动转身重定向到当前 Kwang 模型，叠加原有持剑奔跑上半身，离线烘焙为独立动画。

## 使用位置

`/Game/Combat/Animations/Native/Kwang/`

- `A_FreePivot_Left` / `A_FreePivot_Right`：60 fps、左右 180° 的成品动画；左侧 1.1 秒，右侧 1.5 秒。
- `AM_FreePivot_Left` / `AM_FreePivot_Right`：已绑定到 `ABP_CombatKwang2D` 的 `FreePivotLeft/Right`。
- `A_Jog_*_Pivot180` / `AM_Pivot_*`：继续用于锁定移动折返。

非锁定时按目标相对角色的有符号转角选左右片段；180° 的正负方向按引擎角度约定选取。135° 等非正后方输入将转角曲线按目标角度缩放，下肢步幅没有做方向扭曲或步幅扭曲。

## 素材与融合

官方样例安装于 `F:/UEproject/GameAnimationSample`。来源：
[Epic Game Animation Sample](https://www.fab.com/listings/880e319a-a59e-4ed2-b268-b32dac7fa016)。

- 左转源：`M_Neutral_Run_Turn_L_180_Rfoot`，使用原片段 0.70–1.80 秒；已去掉旧成品开头 0.40 秒（24 帧）直跑段。
- 右转源：`M_Neutral_Run_Turn_R_180_Lfoot`，使用原片段 0.60–2.10 秒。
- 上半身源：项目现有 `A_Jog_Fwd`，按原周期循环采样；左侧起始相位 0.4 秒、右侧 0，保留裁切前的持剑动作相位。
- 保留官方重定向动作的骨盆、腿和脚；`spine_01/02/03` 的持剑源权重为 0.15/0.45/0.85。
- 胸部子骨骼（肩、手臂、扭转骨、手指、武器、肩甲、头部）使用持剑源局部姿态。两侧手臂和武器作为同一个姿态整体保留。
- 手脚 IK 辅助骨骼按最终融合结果重新定位。
- 去除根骨位移和旋转，根转角保存为 `PivotYaw` 曲线。动画没有 Root Motion。

### 持剑出口相位校准（2026-09-23）

`align_pivot_sword.py` 在末尾 0.50–0.25 秒之间用平滑权重让脊柱恢复到同相位 `A_Jog_Fwd` 姿态，再用双骨 IK 校准两手位置和手腕方向。骨盆、下肢和 `PivotYaw` 不变，手指和武器局部姿态保留；IK 保持手臂骨长，目标超出自然可达范围时不拉伸手臂。原始融合片段保存在 `Retarget/SwordPhaseSource`，磁盘备份在 `Saved/Backups/PivotSwordPhase`。

新增 `PivotUpperPhase`（未取模的跑步周期相位）和 `PivotSwordMatch`（尾段校准权重）曲线。运行时在 Pivot 完全遮住 BS、已反向加速、速度达到 Jog 阈值、朝向误差不超过 5° 时，按该曲线对齐底层 BS 的时间；淡出期间不再跳转底层时间。低速、可见底层或其他动作不会被强制改相位。

当前 `Pivot.PlayRate = Animation.PlayRate = 1`、提前 0.2 秒开始淡出、淡出 0.14 秒的配置，已验证两方向、三种不同起跑相位。实际混合阶段刀尖相对目标跑步姿态误差：右侧最大约 0.83 cm，左侧约 4.15 cm。只做相位匹配而不修正上半身，仍会因局部旋转链混合放大刀尖偏移。

这项校准针对非锁定 Pivot 返回前向跑步的出口。若改变播放倍率关系或提前到校准区间之前退出，应重新核对交接；入场仍使用原有融合。

重新生成：`align(write=True, source_root='/Game/Combat/Animations/Retarget/SwordPhaseSource/')`。验证：`Tools/tests/pivot_sword_phase_regression.py`，报告 `Saved/Acceptance/PivotSwordPhaseRuntime.json`。

源片段的工作副本已去掉样例通知，依赖从 1187 项缩减到 16 项再迁入项目；原始 Paragon 动画没有改写。保留源骨架、源片段、IK Rig、Retargeter 和未融合重定向片段，便于重新制作。

## 控制与调参

位移仍由 `CombatMovementComponent` 按原刹车与反向加速配置计算，没有消费动画根位移。

非锁定新动作通过直接采样片段 `PivotYaw` 曲线控制胶囊朝向，采样不受蒙太奇融合权重影响；因此 **Pivot.TurnRate / TurnDelay 不再控制这两段新动作**。这两项保留给没有配置新动作的旧路径。锁定朝向维持原逻辑。

- `Pivot.PlayRate`：同时改变动作和曲线转身速度。
- `Pivot.BrakingDeceleration`、`ReverseAcceleration`：仍控制逻辑刹车和反向提速。
- `ReverseMinProgress`、`ReverseDelay`、`ReverseMaxFacingAngle`：仍限制反向起步。
- 新动作启用提前退出时，还需朝向距目标不超过 5°，防止尚未转完就切回普通跑。

没有修改当前 Data Asset 的数值。由于仍是代码驱动位移，这一版解决了动作类型、持剑姿态和转向时序，**不保证任意进入速度下脚底严格锁地**；若要完全贴脚，需要后续按片段配置速度包络、距离匹配或步幅扭曲。

## 制作和检查

- `prepare_kwang_retarget.py`：目标 IK Rig。
- `inspect_official_pivots.py`：在官方样例中采样根轨迹、制作无通知工作副本及依赖清单。
- `retarget_official_pivots.py`：建立自动骨链匹配、姿态对齐及全身 IK 的 Retargeter，导出 Kwang 片段。
- `bake_sword_pivot.py`：逐骨骼融合、重新生成辅助 IK、烘焙根转角曲线。
- `configure_free_pivots.py`：生成蒙太奇并绑定动画蓝图。
- `preview_sword_pivots.py`：临时预览角色与拍摄；不保存到竞技场。

Development Editor 编译通过。`sword_pivot_assets.py` 检查左右共 158 帧：根位移和根转角为零，下肢与重定向结果一致，手指及武器局部姿态保留。持剑出口校准后，手臂和脊柱尾段按上述方法修正，另验证刀尖与同相位跑步目标的偏差。

2026-09-23：`trim_left_pivot.py` 移除左侧原成品前 24 帧，保留剩余姿态和持剑相位，重设 `PivotYaw` 起点为 0、终点为 -180°，并将左蒙太奇片段及总时长更新为 1.1 秒。原资产备份位于 `Saved/Backups/LeftPivotTrim`。从原重定向片段重新生成左侧时，使用 `bake(..., start=.7, end=1.8, upper_phase=.4)`。

PIE 已验证左右 135°、180° 的动作选择、结束朝向及锁定动作分离。后续测试范围按用户要求限于转身、持剑姿态与移动衔接，技能、起跳、松键不作为本次后续验收范围。

报告：`Saved/Acceptance/SwordPivotAssets.json`、`FreePivotRegression.json`。
预览：`Saved/Acceptance/SwordPivotLineup.png`（后排右转，前排左转；按画面从右到左为动作前进时间，0.05/0.40/0.70/1.00/1.40 秒）。
