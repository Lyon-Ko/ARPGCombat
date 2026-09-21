# Combat editor automation

Engine: `D:\UE5.8\UE_5.8` (5.8.2). Override with `-Engine` on the PowerShell entry point or `COMBAT_ENGINE` for direct Python.

```powershell
& .\Tools\Combat.ps1 doctor
& .\Tools\Combat.ps1 build   # close the editor gracefully first
& .\Tools\Combat.ps1 editor
& .\Tools\Combat.ps1 assets -Path /Game
& .\Tools\Combat.ps1 test
& .\Tools\Combat.ps1 python -File D:\UEproject\Combat\Tools\smoke_test.py
& .\Tools\Combat.ps1 python -Code 'import unreal; print(unreal.Paths.project_dir())'
& .\Tools\Combat.ps1 play -Action start
& .\Tools\Combat.ps1 play -Action stop
```

`combat_remote.py` uses Epic's engine-bundled `remote_execution.py`; no server on port 8001 is required. Discovery is local multicast (TTL 0, loopback 127.0.0.1, UDP 6766). Every command verifies the exact project root and project name. The callback TCP port is chosen dynamically. Execute editor commands sequentially: Epic's editor remote protocol maintains one command connection at a time.

The direct CLI needs only the engine Python (3.11.8), with no extra packages:

```powershell
& 'D:\UE5.8\UE_5.8\Engine\Binaries\ThirdParty\Python3\Win64\python.exe' .\Tools\combat_remote.py status
& 'D:\UE5.8\UE_5.8\Engine\Binaries\ThirdParty\Python3\Win64\python.exe' .\Tools\combat_remote.py run_python --file .\Tools\smoke_test.py
```

The optional stdio MCP bridge uses `uv sync --project Tools` and `uv run --project Tools python Tools/combat_mcp.py`. Its four tools are `status`, `run_python`, `list_assets`, and `pie`. Project configuration is `.codex/config.toml`; no global MCP configuration is modified. A current Codex task may need to be reopened to discover newly added project MCP tools; the CLI works immediately. MCP dependencies are locked in `Tools/uv.lock`.

Original baseline: commit `c151f64`; backup `D:\UEproject\Combat_Backups\Original_20260922_004303` (244 files, Config + Content 135148061 bytes, counts and bytes verified before edits). Build/cache/output folders are ignored; Unreal assets use Git LFS. No remote Git origin is configured.
