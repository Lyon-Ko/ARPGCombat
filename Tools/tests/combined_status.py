import builtins,json,unreal as u
r=builtins._combat_combined_sources
print(json.dumps({'status':r.report['status'],'callback_active':r.handle is not None,'held_keys':list(r.held_keys),'delegates':len(r.bindings),'restored':r.report.get('temporary_definition_restored'),'cleanup_errors':r.report.get('cleanup_errors'),'paused':u.GameplayStatics.is_game_paused(r.world)}))
