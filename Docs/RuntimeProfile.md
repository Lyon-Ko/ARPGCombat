# 补充运行时性能采样

`Tools/profiling/runtime_profile.py` 是独立 opt-in 补充工具。正式 20 场仍使用 `Tools/tests/start_acceptance.py` 的现有同步完整证据保存流程，两份结果都必须保留；本工具不能替代正式验收，也不能用来抹掉正式采样中的长帧。

工具已实际执行。延后写盘、GC观测、CPU trace与Mass串行控制采样的报告、真实失败及版本限制见 [Performance](Performance.md)。本页说明复现方法，最终结果以各份报告的实际状态为准。

## 保持一致和唯一差异

通过继承 Acceptance / ArenaRegression 复用现有实现，不复制大型输入机器人。保留实际1920×1080视口断言、High与100%分辨率CVar回读、运行时DLL SHA-256/硬件元数据、真实公共输入方法、Boss StateTree、伤害/特效/命中停顿及全部事件、断言和随机种子。先运行原有input_cases、defense_cases、lifecycle_cases作为60fps预热。默认三场，也可用 `start(fights_per_cap=10)` 运行十场；参数仅接受3–10的整数。最后一场按原有单档策略不发攻击/格挡/短冲输入，覆盖真实被动败局；十场即9主动+1被动。

CSV在第一场自然对局前开始，所选最后一场连同重试检查结束后STOP，包含所有场次、重置、回调和所有长帧。`warmup_frames_to_exclude=0`，不删慢帧、不修改画质/血量/招式/容差。

唯一有意改变的测量条件是报告写盘策略：采样期间每次 save 请求仅增加固定计数并更新 last_save，完整事件及断言对象仍保留在内存，不做事件抽样或裁剪。STOP 后继续抑制大报告写盘；沿用原入口的文件完成检查，并额外等待至少 2 秒、CSV 大小/mtime 至少 1 秒稳定，再计算哈希、完成正常清理后一次保存完整报告。这样不会在 STOP 同帧用大 JSON 序列化污染尾帧。CSV 稳定不是格式有效性的证明，仍需离线解析。

这一结果描述“延迟证据写盘的同一测试机器人场景”，不是纯手动游戏基准。回调、内存中事件收集和其他测试逻辑开销仍然存在；差异不能预先全归因写盘。进程异常退出会失去尚未落盘的内存证据，因此正式 20 场不能采用该策略来替代原流程。

## 执行方法

要求已有浮动 PIE，脚本不会打开工程或启动 PIE。确保没有其他测试控制角色或采集性能，再由唯一 remote 执行者调用：

```python
import runpy
profile = runpy.run_path(r'D:\UEproject\Combat\Tools\profiling\runtime_profile.py')
profile['start'](fights_per_cap=10)  # 默认不传参数时为3场
# 在后续调用查询，不要循环阻塞 Slate：
profile['status']()
# 提前中止会先停止 CSV 并等待文件稳定，active 可能暂时仍为 true：
profile['stop']()
```

start检查现有正式/独立runner，并占用共同识别的 `_combat_arena_regression` 标记，禁止并发。不要在draining时启动其他测试或关闭PIE；等待active=false。停止请求立即释放按键和攻击按住状态；提前停止记录stopped，异常或CSV未完成记录failed。文件检查/哈希异常也进入一次性finalize，保留错误并执行恢复及回调解除；最终写盘失败时错误留在builtins并输出UE日志。正常清理恢复帧率上限、GPU CSV开关、AI种子、输入/委托并解除Slate回调；High沿用会话配置。planned_passive_death_round记录所选最后一场，即默认第3场或十场模式的第10场。

输出为 `Saved/Acceptance/runtime_profile_<UTC>.json` 与 `Saved/Profiling/CSV/Combat_Supplemental_1080pHigh_60_<UTC>.csv`。报告固定 `supplemental_profile=true`、`accepts_twenty_rounds=false`；记录实际所选场数、完整断言、write_strategy、延迟save次数、画质/视口、DLL标识、每场seed和CSV哈希。补充三场或十场都不等于正式20场。

离线分析全部原始 CSV：

```powershell
& 'D:\UEproject\Combat\Tools\.venv\Scripts\python.exe' 'D:\UEproject\Combat\Tools\tests\analyze_performance.py' '<补充CSV绝对路径>' --warmup-frames 0 --output '<补充分析JSON绝对路径>'
```

与正式结果比较时必须并列标明运行时版本、采样帧数、不同预热/场次数、保存策略和全部长帧。正式 20 场的通过与否仍完全由正式报告决定。AST/静态检查不代表真实 UE 执行或反射已验证。
