# Locomotion 实时参数表

配置资产：`/Game/Combat/Config/DA_Locomotion`（CombatLocomotionConfig Data Asset）。
在内容浏览器双击资产，在 Details 面板按分类调参。PIE 中修改数值约 0.2 秒内生效，无需先保存；结束 PIE 后 Ctrl+S 保存，跨会话保留。
玩家蓝图的 `Locomotion Config` 已绑定此资产；运行时不再读取 INI。
控制台命令 `Combat.Locomotion.Reload` 可立即重载。屏幕显示配置版本、速度、加速度、Pivot 阶段。
Details 提供数值范围约束和中文提示。字段之间的关系错误时保留上次有效配置，修正后自动恢复。

默认 Pivot：以 900 cm/s² 刹车，转向速度 900°/s；刹停且朝向达标后以 1200 cm/s² 反向加速。
反向加速可以发生在完整 Pivot 动画播放期间。素材不裁剪，播放倍率默认 1；EarlyExitEnabled 默认关闭。
调小 BrakingDeceleration 会延长刹车；调大 ReverseAcceleration 会更快反向起步；TurnRate 控制转向快慢。

仅作用于玩家。碰撞、重力、地面检测仍由 CharacterMovement 处理；技能可打断所有 Pivot 阶段。
修改倍率/转向/加速度可作用于正在进行的动作；BlendIn 只影响下次入场，已经开始的淡出不重新计时。
骨骼、片段引用、技能伤害/判定通知等仍属于原资产。动画图的 Grounded/Airborne 状态过渡在 ABP 中调整。

| 分类 | 键 | 默认值 | 范围 | 说明 |
|---|---|---:|---|---|
| Movement | `ForwardSpeed` | 560 | 1～3000 | 前进最高速度 cm/s |
| Movement | `BackwardSpeed` | 560 | 1～3000 | 后退最高速度 cm/s |
| Movement | `LeftSpeed` | 560 | 1～3000 | 左移最高速度 cm/s |
| Movement | `RightSpeed` | 560 | 1～3000 | 右移最高速度 cm/s |
| Movement | `Acceleration` | 1600 | 1～20000 | 普通移动加速度 cm/s² |
| Movement | `GroundFriction` | 4 | 0～50 | 普通移动转向摩擦 |
| Movement | `BrakingDeceleration` | 1200 | 0～20000 | 松键刹车减速度 cm/s² |
| Movement | `BrakingFriction` | 0 | 0～50 | 松键独立刹车摩擦 |
| Movement | `BrakingFrictionFactor` | 1 | 0～10 | 普通刹车摩擦倍率 |
| Movement | `TurnRate` | 900 | 1～3600 | 自由移动转向角速度 °/s |
| Movement | `LockedTurnInterpSpeed` | 12 | 0.1～100 | 锁定目标时朝向插值速度 |
| Movement | `InputDeadZone` | 0.01 | 0～0.95 | 移动输入死区 |
| Pivot | `Enabled` | true | true / false | 启用折返 |
| Pivot | `MinSpeed` | 160 | 0～3000 | 折返触发最低水平速度 cm/s |
| Pivot | `MinAngle` | 120 | 90～180 | 速度与新输入夹角阈值 ° |
| Pivot | `Cooldown` | 0.25 | 0～5 | 折返结束或打断后冷却 s |
| Pivot | `CancelAngle` | 60 | 1～180 | 新输入偏离折返目标多少度时取消 ° |
| Pivot | `CancelOnRelease` | true | true / false | 松键是否取消折返 |
| Pivot | `CancelOnLockChange` | true | true / false | 切换锁定是否取消折返 |
| Pivot | `BrakingDeceleration` | 900 | 1～20000 | 折返刹车减速度 cm/s²；560速度约0.62秒刹停 |
| Pivot | `BrakingFriction` | 0 | 0～50 | 折返刹车附加摩擦；0为纯恒定减速度 |
| Pivot | `StopSpeed` | 5 | 0～100 | 低于此速度允许切换反向加速 cm/s |
| Pivot | `ReverseAcceleration` | 1200 | 1～20000 | 折返反向起步加速度 cm/s² |
| Pivot | `ReverseFriction` | 0 | 0～50 | 反向加速阶段转向摩擦 |
| Pivot | `ReverseDelay` | 0.1 | 0～10 | 触发后允许反向起步的最早时间 s |
| Pivot | `ReverseMinProgress` | 0 | 0～1 | 反向起步所需最小动画进度 0..1 |
| Pivot | `ReverseMaxFacingAngle` | 45 | 0～180 | 自由移动时朝向距目标小于此角才允许反向起步 ° |
| Pivot | `TurnDelay` | 0.02 | 0～10 | 触发后延迟多久开始转向 s |
| Pivot | `TurnRate` | 900 | 1～3600 | 折返转向角速度 °/s；不再绑到整个片段时长 |
| Pivot | `PlayRate` | 1 | 0.05～4 | 完整Pivot片段播放倍率；不会裁剪源片段 |
| Pivot | `BlendIn` | 0.07 | 0～2 | Pivot进入融合 s；下次触发生效 |
| Pivot | `BlendOut` | 0.14 | 0～2 | Pivot自然结束融合 s |
| Pivot | `InterruptBlendOut` | 0.08 | 0～2 | Pivot被技能等打断时融合 s |
| Pivot | `BlendOutTriggerTime` | 0 | -1～5 | 距片尾多久开始融合 s；0播完整段；-1自动 |
| Pivot | `EarlyExitEnabled` | false | true / false | 反向达到速度后是否提前融合回locomotion；默认完整播放 |
| Pivot | `ExitMinProgress` | 0.65 | 0～1 | 提前退出所需最小动画进度 |
| Pivot | `ExitMinSpeed` | 350 | 0～3000 | 提前退出所需反向速度 cm/s |
| Animation | `PlayRate` | 1 | 0.05～4 | 地面BlendSpace播放倍率；独立于技能和Pivot |
| Animation | `JogSpeed` | 350 | 1～3000 | 真实速度达到此值时到达Jog采样位置 cm/s |
| Animation | `FastSpeed` | 650 | 2～4000 | 真实速度达到此值时到达最高速度采样位置 cm/s |
| Animation | `SpeedInterp` | 0 | 0～100 | 动画速度参数平滑强度；0立即更新 |
| Animation | `DirectionInterp` | 0 | 0～100 | 动画方向参数平滑强度；0立即更新 |
| Animation | `IdleDirectionSpeed` | 5 | 0～100 | 低于此速度保持上次动画方向，避免停步抖动 cm/s |
| Air | `JumpVelocity` | 650 | 1～3000 | 起跳速度 cm/s |
| Air | `GravityScale` | 1.8 | 0.01～10 | 重力倍率 |
| Air | `AirControl` | 0.7 | 0～1 | 空中控制比例 |
| Air | `BrakingDeceleration` | 0 | 0～20000 | 空中刹车减速度 cm/s² |
| Air | `LateralFriction` | 0 | 0～50 | 空中横向摩擦 |
| Air | `JumpCount` | 2 | 1～10 | 最大跳跃次数，取整数 |
| Air | `MaxHangBudget` | 0.25 | 0～2 | 空中攻击最大滞空预算 s |
| Air | `PlungeHoldTime` | 0.28 | 0～3 | 空中长按攻击触发下劈的时间 s |
| Dash | `Distance` | 250 | 1～3000 | 闪避移动距离 cm |
| Dash | `Duration` | 0.23 | 0.01～0.25 | 闪避移动时长 s；上限匹配当前0.255秒技能结束通知 |
| Dash | `DirectionStep` | 45 | 1～180 | 闪避方向量化角度 ° |
| SkillBlend | `StopOnGroundSkill` | true | true / false | 地面技能开始时是否清零普通移动速度 |
| SkillBlend | `AllowMovementRecovery` | true | true / false | 总开关：允许移动取消已开放取消窗口的普攻后摇 |
| SkillBlend | `InputBufferTime` | 0.18 | 0～1 | 技能输入缓存时间 s |
| SkillBlend | `OverrideBlendOut` | true | true / false | 由本表覆盖玩家技能结束和打断融合时间 |
| SkillBlend | `LocomotionBlendOut` | 0.14 | 0～2 | 玩家技能正常结束回移动的融合时间 s |
| SkillBlend | `InterruptBlendOut` | 0.08 | 0～2 | 玩家技能被打断融合时间 s |
| Camera | `Distance` | 560 | 50～3000 | 自由镜头距离 cm |
| Camera | `OffsetX` | 0 | -1000～1000 | 镜头SocketOffset X cm |
| Camera | `OffsetY` | 45 | -1000～1000 | 镜头SocketOffset Y cm |
| Camera | `OffsetZ` | 85 | -1000～1000 | 镜头SocketOffset Z cm |
| Camera | `FOV` | 90 | 30～140 | 视野角 ° |
| Camera | `Sensitivity` | 1 | 0.01～10 | 鼠标镜头灵敏度 |
| Camera | `Collision` | true | true / false | 镜头碰撞开关 |
| Camera | `ProbeSize` | 12 | 1～100 | 镜头碰撞探针半径 cm |
| Camera | `PositionLag` | false | true / false | 镜头位置延迟开关 |
| Camera | `PositionLagSpeed` | 10 | 0.1～100 | 镜头位置延迟跟随速度 |
| Camera | `RotationLag` | false | true / false | 镜头旋转延迟开关 |
| Camera | `RotationLagSpeed` | 10 | 0.1～100 | 镜头旋转延迟跟随速度 |
| Camera | `LockedTargetWeight` | 0.4 | 0～1 | 锁定构图中心向目标偏移比例 |
| Camera | `LockedPitchMin` | -35 | -89～89 | 锁定镜头最小俯仰角 ° |
| Camera | `LockedPitchMax` | -8 | -89～89 | 锁定镜头最大俯仰角 ° |
| Camera | `LockedRotationInterp` | 4 | 0.1～100 | 锁定镜头旋转插值强度 |
| Camera | `LockedDistanceScale` | 0.65 | 0～5 | 锁定时目标距离对臂长的倍率 |
| Camera | `LockedDistanceBias` | 400 | 0～3000 | 锁定镜头臂长基础偏移 cm |
| Camera | `LockedMinDistance` | 550 | 50～3000 | 锁定镜头最短臂长 cm |
| Camera | `LockedMaxDistance` | 1000 | 50～5000 | 锁定镜头最长臂长 cm |
| Camera | `LockedDistanceInterp` | 3 | 0.1～100 | 锁定镜头距离插值强度 |
| Camera | `FreeDistanceInterp` | 4 | 0.1～100 | 自由镜头距离恢复插值强度 |
| Camera | `HideDistance` | 220 | 0～1000 | 近镜头隐藏自身距离 cm |
| Camera | `RevealDistance` | 270 | 0～1000 | 恢复自身显示距离 cm，须大于HideDistance |
| Camera | `SoftLockRange` | 650 | 0～10000 | 技能辅助朝向目标距离 cm |
| Camera | `SoftLockViewDot` | 0.4 | -1～1 | 技能辅助朝向目标视线点积阈值 |
| Debug | `Overlay` | true | true / false | PIE画面显示配置版本、速度、加速度和Pivot阶段 |
| Debug | `MovementVectors` | false | true / false | 可视化逻辑移动向量；绿=普通移动目标，黄=Pivot刹车目标，紫=反向加速目标，橙=技能位移，蓝=水平速度 |
| Debug | `MovementVectorLength` | 180 | 20～1000 | 逻辑移动箭头长度 cm；蓝色速度箭头随速度相对上限缩放 |
| Debug | `MovementVectorHeight` | 25 | 0～300 | 箭头起点相对胶囊底部的高度 cm |
