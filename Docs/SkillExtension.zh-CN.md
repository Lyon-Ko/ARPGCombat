# 用蓝图、Montage 和数据资产扩展技能

本文针对当前 Combat 工程的实际接口和 `Tools/editor/generate_skills.py`。扩展普通近战、位移、投射物或范围技能，可以复制现有资源并组合现有节点，不需要修改 C++。新增 Gameplay Tag 应在项目设置中登记，不必加入原生标签源码。

**状态说明：** 本文涉及的运行时字段已完成构建。CrescentBurst 独立新标签已有一次 PIE 接链、伤害和正常结束验证，范围见第 8 节。完整 20 场、取消/死亡回归与最终视觉验收仍需分别核对，不能由单例或蓝图编译推断通过。

## 1. 找到可复制的模板

内容浏览器路径对应如下：

| 用途 | 资源路径 |
| --- | --- |
| 第一段玩家剑击 GA | `/Game/Combat/Abilities/GA_Attack1` |
| 第四段终结剑击 GA | `/Game/Combat/Abilities/GA_Attack4` |
| 范围攻击 GA | `/Game/Combat/Abilities/GA_Boss_AOE` |
| 侧跃投射物 GA | `/Game/Combat/Abilities/GA_Boss_LeapLeft` |
| 对应剑击 Montage | `/Game/Combat/Animations/Native/Kwang/AM_Attack1`、`/Game/Combat/Animations/Native/Kwang/AM_Attack4` |
| 对应剑击数据 | `/Game/Combat/Skills/DA_Attack1`、`DA_Attack4` |
| 玩家角色蓝图 | `/Game/Combat/Characters/BP_CombatPlayer` |
| Boss 角色蓝图 | `/Game/Combat/Characters/BP_CombatBoss` |
| 玩家 2D 动画蓝图 | `/Game/Combat/Animations/Native/Kwang/ABP_CombatKwang2D` |
| Boss 2D 动画蓝图 | `/Game/Combat/Animations/Native/Greystone/ABP_CombatGreystone2D` |

生成器定义了 19 个 GA，每个图都使用同一套可编辑事件分支，差异主要来自 Montage 和数据：

| 组别 | SkillTag 后缀；GA / DA / AM 文件名后缀 |
| --- | --- |
| 地面四连 | `Attack1`、`Attack2`、`Attack3`、`Attack4` |
| 玩家其他动作 | `DashStrike`、`Air1`、`Air2`、`Plunge`、`Parry`、`Riposte`、`Dash` |
| Boss 三连 | `Boss.Combo1`、`Boss.Combo2`、`Boss.Combo3`；文件名用 `Boss_Combo1` 等 |
| Boss 特殊动作 | `Boss.AOE`、`Boss.DashSlash`、`Boss.LeapLeft`、`Boss.LeapRight`、`Boss.LeapBack`；文件名中的点同样改成下划线 |

完整标签均以 `Combat.Skill.` 开头。例如 `Combat.Skill.Boss.AOE` 对应 `/Game/Combat/Abilities/GA_Boss_AOE`、`/Game/Combat/Skills/DA_Boss_AOE`、`/Game/Combat/Animations/Native/Greystone/AM_Boss_AOE`。`generate_skills.py` 生成基础 GA 图，`generate_native_characters.py` 再绑定最终 Kwang/Greystone 原生 Montage 和 2D 动画蓝图；早期 `/Animations/Montages` 模板不能替代当前数据中的实际 Montage 引用。

生成 pipeline 会重写基础 GA、数据、动画或表现绑定。扩展资源请复制到各自的 `Custom` 子目录，并保存自定义接入步骤；不要直接修改会被生成器覆盖的基础资源后又无保护地重跑 pipeline。

## 2. 建立一个真正独立的新技能

下面以地面剑技“弧月斩”为例。使用独立目录可避免重新运行基础生成器时覆盖手工资源。

1. 打开 **项目设置 / Project Settings**，搜索 **Gameplay Tags**。通过标签管理界面新增 `Combat.Skill.CrescentCut`，选择项目的配置标签源，例如 `DefaultGameplayTags.ini`，保存设置。确保配置标签导入启用。然后确认该标签能在资源的标签选择器中选中；只在文本框里输入一个尚未登记的名字不够。
2. 在内容浏览器中复制 `GA_Attack1` 为 `/Game/Combat/Abilities/Custom/GA_CrescentCut`。其父类必须是 `CombatGameplayAbility`。
3. 复制兼容当前角色 Skeleton 的 Montage，为 `/Game/Combat/Animations/Montages/AM_CrescentCut`。需要换动作时，在 Montage 中替换动画段，并重新布置通知。不要把不同 Skeleton 的动画直接塞进 Montage；先使用对应骨架的动画或完成重定向。
4. 复制 `DA_Attack1` 为 `/Game/Combat/Skills/Custom/DA_CrescentCut`。也可通过“杂项 → 数据资产”选择 `CombatSkillDefinition` 新建。
5. 设置数据的 `SkillTag=Combat.Skill.CrescentCut`、`AbilityClass=GA_CrescentCut`、`Montage=AM_CrescentCut`。`AbilityClass` 选择生成的蓝图类，不是 Montage 或数据本身。
6. 打开 `BP_CombatPlayer` 的类默认值，把新数据加入 `SkillDefinitions`。同一个角色的数组中，一个 `SkillTag` 只保留一个定义。技能通过这个数组授予 GAS；仅把资源放进内容浏览器不会自动授予。
7. 按下一节选择输入或连段接入方式，编译保存 GA、角色蓝图和数据，退出当前 PIE 后重新开始，让角色重新授予技能。

新增普通 SkillTag 不会自动获得 `Dash`、`Parry`、`Riposte` 等现有特殊技能的原生专用行为。新技能应明确使用现有可组合节点、数据和效果完成所需逻辑。

## 3. 选择输入、条件和连段

| 参数 | 用途与实际行为 |
| --- | --- |
| `SkillTag` | 技能唯一身份；用于查找授予的能力、冷却及连段目标。 |
| `InputTag` | 输入分类。现有左键使用 `Combat.Input.Attack`，右键使用 `Combat.Input.Parry`，Shift 使用 `Combat.Input.Dash`。留空表示不由这些主输入直接挑选，仍可通过连段或 `RequestSkillByTag` 调用。 |
| `Priority` | 同一 InputTag 内，先排除条件、冷却和空中预算不满足的定义，再按优先级从高到低尝试。不要依赖同优先级时的隐含顺序。 |
| `ActivationQuery` | 检查角色 ASC 当前拥有的 Gameplay Tags。空查询代表无额外标签要求。直接 `RequestSkillByTag` 也会检查查询，不是强制绕过入口。 |
| `NextSkillTag` | 当前技能的后继。玩家再次按攻击时请求该标签；Boss 执行任务也会沿链接继续。必须把后继的数据授予同一角色，避免无出口的循环链。 |
| `bCanInterrupt` | 新技能是否允许越过当前技能的取消/连段窗口。它描述新技能的切入能力，并不代表当前技能永久可取消。 |

当前生成器的派生优先级是 `Riposte=100`、`DashStrike=60`、`Air1=40`，基础地面剑击为 0。它们分别要求 `Combat.State.RiposteReady`、`Combat.State.Dashing`、`Combat.State.Air`。地面 `Attack*` 的生成查询排除 `Combat.State.Air`。

**作为新的连段后继：** 新技能 `InputTag` 留空，将 `DA_Attack3.NextSkillTag` 改为 `Combat.Skill.CrescentCut`。新技能的 `NextSkillTag` 留空表示结束该链。这不会改变左键首段的选择。

**作为条件派生：** 设 `InputTag=Combat.Input.Attack`、合适的 `Priority`，在查询编辑器中选择“匹配所有标签 / Match All Tags”，加入所需状态。无条件的高优先级技能会替代普通左键首段，不会自动成为偶尔出现的特殊招式。

**使用新按键：** 在角色蓝图中添加所需输入事件，再调用 `RequestSkillByTag` 或 `RequestSkillByInputTag`。仅登记新的 `InputTag` 不会创建键位绑定；现有 C++ 输入只主动请求上述三个输入分类。

当前输入缓冲为 0.18 秒。过早按下下一段可能在窗口开启前过期；请通过 Montage 的 `ComboOpen` / `Cancelable` 通知安排节奏。当前生成器允许 Dash、Parry、DashStrike、Riposte、Plunge 切入，以支持对应派生。

## 4. 保留 GA 图的真实事件链

打开复制的 GA 的 **Gameplay Ability Graph**，检查以下连接：

```text
Event ActivateAbility
  → Combat Play Montage And Events
      Montage ← GetSkillDefinition → Montage
      OnCompleted   → CompleteSkill(bInterrupted=false)
      OnInterrupted → CompleteSkill(bInterrupted=true)
      OnEvent       → EventTag 相等比较 → Branch → 角色逻辑块
```

角色逻辑块的 Target 连接 `GetCombatCharacter`。生成器使用九个顺序标签分支：True 执行对应块，False 接下一个比较。节点不是注释或截图，修改分支会改变实际执行行为。

**不要把 OnInterrupted 接成正常完成。** 必须显式给 `CompleteSkill` 的 `bInterrupted` 引脚勾选 true，否则技能可能提前按正常结束清理，使中断专用的投射物清理失效。保留任务的正常完成和中断出口，即使 Montage 中也有 `Finish` 通知。

Montage 必须走当前角色普通 AnimInstance 的 `DefaultSlot`。不要为攻击切成 Single Node 动画模式。任务从数据读取 Montage；不需要再额外调用一次 `Play Anim Montage`，否则可能互相中断。

## 5. 在 Montage 中放置九类通知

打开 Montage，在通知轨道中添加 **Combat Gameplay Event**（类 `CombatAnimNotify_Event`），在详情中设置 `EventTag`。每个通知是一个时间点；不要把通知对象当成保存当前目标或命中列表的地方。

| EventTag | GA 调用的角色块 | 放置位置及用途 |
| --- | --- | --- |
| `Combat.Event.HitOpen` | `OpenHitWindow` | 剑刃开始有效接触的时刻；开启扫掠、开启拖尾并播放本次挥击音。 |
| `Combat.Event.HitClose` | `CloseHitWindow` | 剑刃离开有效攻击阶段时关闭检测和拖尾。 |
| `Combat.Event.Move` | `StartSkillMovement` | 推进、侧跃或下劈位移真正开始的时刻。默认参数读取当前数据；显式 Direction 引脚会覆盖数据方向。 |
| `Combat.Event.Projectile` | `EmitSkillProjectile` | 波刃/投射物离手时刻；按该刻的目标位置确定方向。 |
| `Combat.Event.AreaWarning` | `ShowAreaWarning` | 记录范围中心并显示预警；必须先于范围释放。 |
| `Combat.Event.AreaRelease` | `DetonateArea` | 发出释放闪光和声音，再等待 `AreaDelay` 后伤害判定；默认延迟 0.18 秒。 |
| `Combat.Event.ComboOpen` | `OpenComboWindow` | 允许衔接后继技能的时间点。当前窗口保持到本技能结束。 |
| `Combat.Event.Cancelable` | `SetCancelable(true)` | 允许其他技能取消当前动作的时间点；当前窗口保持到结束。 |
| `Combat.Event.Finish` | `FinishSkill` | 正常结束当前技能并清理。不要放在仍需结算的伤害之前。 |

例：普通剑击可设置 `Move → HitOpen → HitClose → ComboOpen → Cancelable → Finish`。多段同一 Montage 可以重复放置若干组 HitOpen/HitClose；每次重新打开是一个新命中窗口。

范围技能必须留出 `AreaRelease + AreaDelay` 的结算时间，再放 `Finish`。提前完成/中断会取消待结算范围计时器。改变 Montage RateScale 或任务 Rate 后，通知在实际游戏中的时间会随播放速度变化；范围延迟仍按游戏世界秒计算。命中停顿只缩放角色，不缩放全局世界时间。

## 6. 调整数值、空中预算和表现资源

| 字段 | 用途 |
| --- | --- |
| `Damage` / `PoiseDamage` | 每个命中窗口或投射物/范围结算的生命、韧性伤害。 |
| `Cooldown` | 从激活开始的 GAS 持续效果冷却，单位秒；正常结束不会立即抹掉它。 |
| `Duration` | 技能安全超时参考，当前看门狗约为此值加 0.3 秒。按实际播放时长填写；现有脚本用 Montage 长度除以 RateScale，任务 Rate 若改动也应计入。正常结束仍应由任务/通知控制。 |
| `MovementDistance` / `MovementDuration` | 位移距离（厘米）和持续时间（秒），通过碰撞扫掠移动。 |
| `MovementDirectionLocal` / `LaunchVelocityZ` | 角色局部方向及起跳初速度。+X 前、±Y 侧、-X 后；向下劈可用世界 Direction `(0,0,-1)`。 |
| `TraceRadius` | 每个剑刃采样点的扫掠半径。实际剑长/端点由角色武器配置决定；`TraceReach` 当前并不控制剑刃扫描长度，不要靠改它扩展攻击距离。 |
| `bGroundOnly` / `bAirOnly` | 分别限制地面/空中，勿同时勾选。地面剑技应设置 bGroundOnly。 |
| `AirAttackIndex` / `AirHangTime` | 两次空中轻击使用 1、2；角色按次序消费预算，落地复位。0 表示不属于这两次轻击，不能用它另做无限空中轻击入口。滞空共享角色 `MaxAirHangBudget`，默认总计 0.25 秒。 |
| `bFaceTarget` | 是否使用目标朝向辅助；短冲/精准格挡通常设 false，避免防御动作自动扭向 Boss。 |
| `bParryable` | 本技能生成的命中是否允许精准格挡。 |
| `AreaRadius` / `AreaHeight` / `AreaDelay` | 范围水平半径、完整高度和释放到命中的间隔；表现体积应与这些数值匹配。 |
| `ProjectileSpeed` | 投射物速度，厘米/秒。角色 `ProjectileClass` 决定实体类型。 |

角色武器配置位于 `BP_CombatPlayer` / `BP_CombatBoss`：独立剑使用 `WeaponMesh`、`WeaponAttachSocket`、`TraceStartSocket` / `TraceEndSocket`；默认为 BladeBase / BladeTip。无端点 Socket 时使用 `WeaponBladeAxis`（默认局部 +X）和 `WeaponBladeLength`。武器已包含在人物 SkeletalMesh 中时启用 `bTraceFromCharacterMesh`，配置实际武器骨/Socket，避免再显示一把独立剑。

可从以下路径选择现有表现资源；复制后可独立调色和调参：

| 数据字段 | 现有资源及行为 |
| --- | --- |
| `TrailEffect` | `/Game/Combat/VFX/NS_BladeTrail`；Boss 可用 `NS_BossBladeTrail`。已使用真实 Niagara Ribbon，跟随剑端，HitOpen 开始、HitClose/结束销毁；最终画面仍需视觉验收。 |
| `HitEffect` | `/Game/Combat/VFX/NS_HitSparks`，确认命中/格挡等反馈时使用。 |
| `CastEffect` | `/Game/Combat/VFX/NS_Projectile` 可作为投射物表现；当前实现也会在技能开始生成一次 CastEffect，纯发射效果需注意不要形成多余的起手爆发。 |
| `AreaReleaseEffect` | `/Game/Combat/VFX/NS_AOEFlash`，在实际 AreaRelease 时生成。 |
| `AreaMesh` / `AreaMaterial` | 原创 `/Game/Combat/VFX/SM_WarningRing` 与 `/Game/Combat/Materials/M_WarningRing`。半径 50cm 的薄 XY 环按 AreaRadius 缩放，保持地面位置；释放时 Opacity 从 .2 升至 .65，结束清理。AreaHeight 只控制实际伤害纵向范围，不拉高地环。 |
| `ProjectileMesh` / `ProjectileMaterial` | 原创 `/Game/Combat/VFX/SM_SwordWave` 与 `/Game/Combat/Materials/M_SwordWave`；局部 +X 传播，Y 宽约 180cm，模型无碰撞。实际伤害盒由 ProjectileCollisionHalfExtent 控制，默认 `(24,85,20)` cm。 |
| `CastSound` | `/Game/Combat/Audio/SW_SwordSwing_01`，其他序号为 02–04；短冲可用 `SW_Dash`，范围爆发可选 `SW_Burst`。默认在首次 HitOpen/Projectile/AreaRelease 播放一次；`bPlayCastSoundAtActivation=true` 才在激活时播放。 |
| `HitSound` / `ParrySound` | `/Game/Combat/Audio/SW_MetalClash_01` 与 `/Game/Combat/Audio/SW_Parry`。 |
| `CueColor` | 范围材质等反馈颜色；Niagara 模板仍须检查其实际暴露的颜色参数。 |

给 Boss 新招时，使用登记过的 `Combat.Skill.Boss.*` 标签并加入 Boss 的 `SkillDefinitions`。当前 StateTree 选择器按此标签前缀筛选，读取 `SelectionWeight`、`MinAIRange` / `MaxAIRange` 和冷却。仅用于三连后续的定义可将 SelectionWeight 设为 0，通过 NextSkillTag 接入；当前 AI 链有安全长度限制。

## 7. 命中去重、取消和 Buff 的作用域

每次 `OpenHitWindow` 都创建新 AttackInstance，并清空本窗口目标集合。相同目标在该窗口只受一次命中；再次关闭并打开才是新一段。运行时还记住同一攻击者最近 64 个 ID，防止旧投射物与新窗口交错时重复处理。手工构造 `FCombatHit` 做测试时，新攻击必须提供新 ID；重复 ID 是去重测试，不是连续伤害。

技能正常结束与中断都会关闭命中窗口、停止技能位移、清理任务监听、临时标签、拖尾和预警，取消尚未结算的范围计时器。中断还销毁该角色记录的在途技能投射物；角色死亡/重试会扫描并删除其拥有的全部投射物。正常完成后已经释放的投射物可继续飞行，不应因此把正常完成也接成 Interrupted。

`ApplyCombatEffect(EffectClass, Level)` 用于**技能期间的临时效果**：其有效 ActiveGameplayEffectHandle 被纳入技能结束清理。瞬时 GE 已发生的属性变化并不会因为移除无效句柄而被“撤销”。

希望 Buff 在动作结束后继续存在时，在 GA 蓝图取得角色 ASC，使用 GAS 标准 `Apply Gameplay Effect to Self` / `Apply Gameplay Effect Spec to Self` 节点，并保存返回的句柄；使用 Has Duration 让其自然到期，或在指定条件下用 `Remove Active Gameplay Effect` 移除。Infinite Buff 必须自行设计死亡、重试和取消规则，不能假定它被 `ApplyCombatEffect` 自动追踪。现有 RiposteReady 是独立 0.8 秒奖励 GE，故不会随精准格挡技能结束一并消失。

## 8. 现有 CrescentBurst 示例实际做了什么

`Tools/editor/generate_skill_example.py` 定义的输出路径是：

- `/Game/Combat/Abilities/Examples/GA_CrescentBurst`
- `/Game/Combat/Animations/Montages/AM_Example_CrescentBurst`
- `/Game/Combat/Skills/Examples/DA_Example_CrescentBurst`

脚本复制 Attack4 的 GA、Montage、数据，在额外 `ExtensionEvents` 通知轨道添加 0.04 秒 AreaWarning 与 0.49 秒 AreaRelease；数据改为 Damage=32、PoiseDamage=55、AreaRadius=260、Cooldown=1.2。按默认 AreaDelay=0.18，未改变播放速度时预计在 0.67 秒结算范围伤害。

初版脚本保留了复制数据中的 `Combat.Skill.Attack4`，只能通过替换玩家 SkillDefinitions 中的 DA_Attack4 来替换终结技行为。现在项目已在 `Config/DefaultGameplayTags.ini` 登记独立标签 `Combat.Skill.Example.CrescentBurst`，无需修改 C++。

独立新增技能的接入方式为：将 `/Game/Combat/Skills/Examples/DA_Example_CrescentBurst` 的 SkillTag 设为 `Combat.Skill.Example.CrescentBurst`，InputTag 留空；把数据加入玩家 SkillDefinitions，保留原 DA_Attack4；临时将 `/Game/Combat/Skills/DA_Attack3` 的 NextSkillTag 指向新标签。测试后恢复原后继和默认技能表。

`Saved/Acceptance/SkillExtensionNewTagPIE.json` 已记录真实 Attack1→Attack2→Attack3→Combat.Skill.Example.CrescentBurst，整条链累计伤害 130（并非 CrescentBurst 单独伤害），`ended_cleanly=true`、`defaults_restored=true`。这证明独立标签接链与该次正常结束，默认玩家未永久替换为此示例。它不覆盖所有中断时机、冷却拒绝、死亡、30/60fps 或最终视觉效果。

复制 Montage 时原有通知会保留，因此示例可能同时包含第四剑的近战命中和新增范围爆发；若设计只需要范围伤害，应检查并移除不需要的 HitOpen/HitClose。复制的 GA 已含九类事件分支，脚本主要增加说明注释，没有新增 C++ 逻辑。

上述通过范围来自已保存的 PIE 记录；本次文档更新未运行编辑器。后续修改示例需重新验证，不能用 `EXTENSION_CREATED` 或蓝图编译成功替代运行证据。

## 9. 新技能交付前的检查

1. GA 和角色蓝图编译无错误；Montage、AbilityClass、DataAsset 引用正确；新增 Tag 可选择，角色只装备一个同 SkillTag 定义。
2. 正常按键或连段确实进入新技能；不满足查询、冷却、地面/空中预算时被正确拒绝。确认高 Priority 没有意外抢走全部普通攻击。
3. 在 30/60fps 下检查剑刃与命中窗口，单窗口只伤害一次、多段能够再次命中；观察拖尾、音效与实际挥剑/释放对齐。
4. 在 HitOpen 前后、位移中、释放预警后中断技能，确认 Busy、伤害窗口、拖尾和延迟伤害无残留。测试死亡与重试，尤其是已释放投射物和额外 Buff。
5. 范围预警、闪光、0.18 秒反应间隔与最终体积一致；取消发生在多目标结算期间时不继续使用已清理技能。该边界修复仍需实际验证。
6. 保存全部资源，冷重启编辑器重新 PIE；记录新技能的按键/连段、命中、取消与视觉证据。完整项目验收另见 `Docs/Acceptance.md`。

尚未完成的验证应直接记录为待办；本指南只给出扩展方法和现有接口契约。
