# Kwang 非锁定持剑折返

已将 Epic Game Animation Sample UE 5.8 的左右跑动转身重定向到当前 Kwang 模型，叠加原有持剑奔跑上半身，离线烘焙为独立动画。

## 使用位置

`/Game/Combat/Animations/Native/Kwang/`

- `A_FreePivot_Left` / `A_FreePivot_Right`：60 fps、1.5 秒、左右 180° 的成品动画。
- `AM_FreePivot_Left` / `AM_FreePivot_Right`：已绑定到 `ABP_CombatKwang2D` 的 `FreePivotLeft/Right`。
- `A_Jog_*_Pivot180` / `AM_Pivot_*`：继续用于锁定移动折返。

非锁定时按目标相对角色的有符号转角选左右片段；180° 的正负方向按引擎角度约定选取。135° 等非正后方输入将转角曲线按目标角度缩放，下肢步幅没有做方向扭曲或步幅扭曲。

## 素材与融合

官方样例安装于 `F:/UEproject/GameAnimationSample`。来源：
[Epic Game Animation Sample](https://www.fab.com/listings/880e319a-a59e-4ed2-b268-b32dac7fa016)。

- 左转源：`M_Neutral_Run_Turn_L_180_Rfoot`，使用原片段 0.30–1.80 秒。
- 右转源：`M_Neutral_Run_Turn_R_180_Lfoot`，使用原片段 0.60–2.10 秒。
- 上半身源：项目现有 `A_Jog_Fwd`，按原周期循环采样，起始相位 0。
- 保留官方重定向动作的骨盆、腿和脚；`spine_01/02/03` 的持剑源权重为 0.15/0.45/0.85。
- 胸部子骨骼（肩、手臂、扭转骨、手指、武器、肩甲、头部）使用持剑源局部姿态。两侧手臂和武器作为同一个姿态整体保留。
- 手脚 IK 辅助骨骼按最终融合结果重新定位。
- 去除根骨位移和旋转，根转角保存为 `PivotYaw` 曲线。动画没有 Root Motion。

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

Development Editor 编译通过。`sword_pivot_assets.py` 检查左右共 182 帧：根位移和根转角为零；下肢与重定向结果一致；持剑手臂、手指及武器与原姿态一致（最大局部角误差小于 0.00006°）。姿态预览检查通过。

PIE 已验证左右 135°、180° 的动作选择、结束朝向及锁定动作分离。后续测试范围按用户要求限于转身、持剑姿态与移动衔接，技能、起跳、松键不作为本次后续验收范围。

报告：`Saved/Acceptance/SwordPivotAssets.json`、`FreePivotRegression.json`。
预览：`Saved/Acceptance/SwordPivotLineup.png`（后排右转，前排左转；按画面从右到左为动作前进时间，0.05/0.40/0.70/1.00/1.40 秒）。
