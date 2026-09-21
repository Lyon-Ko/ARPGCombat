import builtins, json, unreal as u
r=builtins._combat_build11_regression
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
print(json.dumps({'status':r.report['status'],'callback_active':r.handle is not None,'held_keys':list(r.held_keys),'delegates':len(r.bindings),'cleanup_errors':r.report.get('cleanup_errors'),'paused':u.GameplayStatics.is_game_paused(w),'cap':u.SystemLibrary.get_console_variable_float_value('t.MaxFPS')}))
