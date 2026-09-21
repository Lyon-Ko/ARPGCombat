import builtins, json, unreal as u
keys=['_combat_arena_regression','_combat_arena_ai_scenarios','_combat_arena_spatial_visual','_combat_arena_ai_near']
rows=[]
for key in keys:
 r=getattr(builtins,key,None)
 if r: rows.append({'runner':key,'status':r.report['status'],'callback_active':r.handle is not None,'held_keys':list(r.held_keys),'delegate_bindings':len(r.bindings),'cleanup_errors':r.report.get('cleanup_errors')})
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
print(json.dumps({'runners':rows,'pie_valid':u.SystemLibrary.is_valid(w),'paused':u.GameplayStatics.is_game_paused(w)}))
