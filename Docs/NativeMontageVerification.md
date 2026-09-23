# 原生 Montage 集成验证

本轮把动画技能时序移至原生 Montage 通知轨道，保留独立派生图。V1 的旧格式和无动画数据技能继续兼容。

## 实际结果

| 验证 | 结果 |
| --- | --- |
| CombatEditor Win64 Development | 编译、链接通过 |
| Combat Win64 Development | 编译、链接通过 |
| Combat.SkillEditor 编辑器 Automation | 4 组通过，包含迁移、源资产保护、撤销恢复及命名窗口校验 |
| 新增原生 Montage PIE 专项 | 41/41 通过 |
| 原有技能编辑器功能回归 | 68/68 通过 |
| 默认四连 30/60fps 回归 | 29/29 通过 |
| 近战＋投射物／范围组合回归 | 17/17 通过 |

原生专项覆盖：旧 Events 不重复执行、通知时间权威、命名窗口派生、缓冲过期、窗口自然结束、取消清理、同一技能重播、两个角色共享同一个 Montage、技能作用域 Buff、连射取消、末帧事件、跳转不补发、暂停窗口保持及连射暂停/恢复。

`MontageSkills_20260923T031221418764Z.json` 保留了修复前两个失败：末帧事件未执行、暂停窗口被提前关闭。修复使用绑定的播放实例编号处理 UE 末帧实例清理，并在暂停位置保留逻辑窗口；最终报告为 `MontageSkills_20260923T031810597699Z.json`。

原生编辑器界面已通过 computer-use 实际观察：动画预览、四类通知轨道、“技能派生”工具栏菜单及其中的 `DA_Strike` 项均可见。独立派生工作台已通过编辑器接口打开，标签页与原生 Montage 并列。后续点击时检测到用户并行操作，未把该次点击跳转计为通过。

## 资产和范围

- 独立示例保存于 `/Game/Combat/SkillEditorExamples/Montage`，两个 Montage、两个技能及一个技能集合。
- 转换使用副本，原有 `/Game/Combat/Animations/Native` 资产未改写。
- 本次未重跑完整 20 场对局。V1 的 495 项历史报告仍保留，不能当作此次原生集成的新增验证。
- 构建哈希、最终报告及失败记录见 [本轮证据目录](Evidence/NativeMontage_20260923/Verification.json)。

制作与迁移步骤见 [原生 Montage 使用说明](NativeMontageSkills.zh-CN.md)。
