# 原生 Montage 技能编排

动画技能现在直接使用 UE 的 Montage 通知轨道编排，派生图继续独立保存在技能数据资产中。无动画技能保留数据时间轴；V1 资产不会在加载时被静默迁移。

## 制作动画技能

1. 新建技能资产，保持 `DataDriven` 与 `UseMontageNotifies` 开启，指定角色骨架兼容的 Montage。
2. 点技能工作台的 **原生 Montage**，或直接双击 Montage。动画技能不再在工作台显示另一套动画预览和时间轴。
3. 在原生通知轨道右键添加：
   - **Combat Skill Action · 技能事件**：配置子弹、Buff、位移、范围预警/释放、特效、声音或结束。发生时间由轨道位置决定。
   - **Combat Skill Window · 技能窗口**：配置近战命中、派生允许或取消窗口。持续时间由通知状态条的起止位置决定。
4. 派生窗口选择 `WindowType=Derivation`，填写名字，例如 `AttackFollowup`。
5. 回到独立派生图，给连线选择输入/命中触发、目标技能、条件和优先级，将 `WindowName` 填为 `AttackFollowup`。原生模式忽略旧 `WindowStart/WindowEnd`，图详情也不再显示这两个字段。
6. 保存 Montage 与技能资产，点击 **检查资产**，再用 **PIE 试玩**验证。

原生 Montage 工具栏新增 **技能派生**下拉菜单，可打开引用此 Montage 的技能配置。一个 Montage 可以由多个技能/角色共用；技能关系、伤害、冷却、互斥和打断策略仍在各技能资产上配置。

空 `WindowName` 表示不限制派生窗口。`Completed` 在技能正常结束后触发，应保持窗口名为空；不要引用此时已经关闭的通知状态。

## 转换旧时间轴

对已有 V1 动画技能，在工作台点 **迁移到 Montage**：

旧的 GA 蓝图技能需先使用 **复制为新版**，得到数据驱动技能，再执行迁移。自定义 GA 蓝图逻辑不在自动转换范围内。

- 创建独立 Montage 副本，原来的共享 Montage 不变。
- 旧瞬时事件转换成 `Combat Skill Action`；命中/取消/连段窗口转换成 `Combat Skill Window`。
- 派生规则的数字起止时间转换成具名通知窗口，连线自动引用这些名字。
- 副本中的已知旧 `Combat Gameplay Event` 通知被移除，其他通知保留。
- 转换成功后清空旧 Events 数组，启用原生模式；不会同时执行两条事件链。
- 支持撤销恢复技能的原 Montage、Events 和执行模式。保存时需同时保存新 Montage 与技能。撤销不会删除已经创建的独立资产。

转换要求合法时间范围、独立目标路径且不在 PIE 中。已包含原生技能通知的未迁移 Montage 会拒绝再次导入，避免重复事件。不要先手动开启原生模式再尝试转换旧 Events。

新通知可以直接在原生编辑器拖动、复制、裁剪、切换轨道和编辑参数；不需要回写自定义时间轴。原生模式下，Action 载荷中的旧 Time 不参与执行且在通知详情隐藏；Movement 的 Duration 仍是该动作的位移持续时间。

## 执行与生命周期

- 通知只保存资产配置，不保存角色、命中集合、Buff 句柄或当前执行序号。
- 运行时检查角色主 Mesh、Montage 资产及播放实例编号。旧实例的回调不会影响同一技能重播后的实例。
- 命名窗口和待发连射按角色分别保存；同一 Montage 多角色共用不会串状态。
- 连射跟随动画播放速度，暂停 Montage 会暂停待发连射；已发出的实体继续自己的飞行生命周期。
- 暂停时保持当前逻辑窗口；跳转到窗口之外会关闭已有窗口，不补发跳过的瞬时事件。
- 原生模式由 Montage 完成/中断控制技能退出，不使用固定世界秒数的结束计时器截断暂停或慢放；播放实例意外消失时执行取消清理。
- 编辑器动画预览不会施加真实伤害或 Buff；真实行为在 PIE 中验证。

## 示例与验证

示例集合：`/Game/Combat/SkillEditorExamples/Montage/DA_MontageSkills`。

- `DA_Strike → DA_Followup` 展示命名窗口派生。
- `AM_Strike`、`AM_Followup` 是独立 Montage，包含技能事件、命中窗口、派生窗口及取消窗口轨道。
- 示例创建脚本：`Tools/editor/generate_montage_skill_examples.py`，已有示例不会被重写。
- 编辑器测试：`Automation RunTests Combat.SkillEditor`，含迁移、源资产保护、撤销和失效窗口引用校验。
- PIE 专项：`Tools/tests/montage_skill_regression.py` 的 `start/status`，使用临时副本测试，不保存测试改动。

本轮实际验证范围见 [原生 Montage 集成验证](NativeMontageVerification.md)。V1 历史验收保留在原交付记录中。
