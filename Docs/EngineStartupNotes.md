# 引擎启动自测日志说明

最终日志 `Saved/Logs/CombatFinalColdStart.log` 在引擎初始化前记录13条 `LogAutomationTest: Error: Condition failed`。启用该日志类别的详细级别后，明确归属为 `FUnifiedErrorTest_CreateErrorMessage` 7条（1933–1940行）、`FUnifiedErrorTest_CreateErrorMessageWithContext` 4条（1941–1945行）、`FStructuredLogFormatTest` 2条（1972–1974行）。这是引擎Core格式化Smoke测试的失败，不是Combat回归断言；原失败保留，不宣称日志零错误，也不将其标成预期负例。

本地UE5.8.2源码 `Engine/Source/Runtime/Core/Tests/Experimental/UnifiedError/UnifiedErrorTests.cpp:479–533` 的前两测试共11个断言，将 `CreateErrorMessage` 返回的FText字符串与硬编码英文比较。对应实现 `Core/Private/Experimental/UnifiedError/UnifiedError.cpp:84、110–125` 明确启用本地化格式化，当前中文日志也显示中文错误文本；这些11项存在明确的本地化结果与英文期望不一致机制。

剩余两条已定位到 `Core/Tests/Logging/StructuredLogFormatTest.cpp`，但当前日志没有逐断言表达式。该文件256–266行的TestLoc使用本地化模板后与固定期望比较；276行期望英文“Found 63 errors!”，335–338行由LOCTEXT构造模板后期望“FText bWorks=true”。这些是本地化敏感候选，不能仅凭两条计数断定具体失败行或把两项全部归因本地化；需要独立更细的格式化输出才能确认。

`Core/Public/Misc/LowLevelTestAdapter.h:130` 将失败CHECK统一写为Condition failed。`Core/Private/Misc/AutomationTest.cpp:31` 默认只显示Warning；531–592运行Smoke测试并汇总，1252打印测试名及结论、1265打印错误。最终冷启动使用 `-LogCmds="LogAutomationTest VeryVerbose"` 才显示完整归属。本项目没有修改引擎、自测、语言或隐藏这些记录。

工程最终只读冷启动报告 `FinalColdStart_20260921T204520545958Z.json` 为359/359通过：33BP、39Montage、216资产、地图、DLL、Attack3.Next=Attack4、Mass=0均核实。工程检查通过与引擎自测错误是不同证据范围，应同时保留。
