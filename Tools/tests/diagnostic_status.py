import builtins, json, unreal as u
r=builtins._combat_arena_regression
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
print(json.dumps({'status':r.report['status'],'callback_active':r.handle is not None,'held_keys':list(r.held_keys),'pie_valid':u.SystemLibrary.is_valid(w),'paused':u.GameplayStatics.is_game_paused(w),'pool':u.SystemLibrary.get_console_variable_float_value('r.Streaming.PoolSize'),'cap':u.SystemLibrary.get_console_variable_float_value('t.MaxFPS')}))
