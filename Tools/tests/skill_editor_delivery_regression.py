"""Sequential compatibility suite. Explicit start only; never overlaps test runners."""
import builtins
import datetime
import json
from pathlib import Path
import runpy
import unreal as u

ROOT=Path(u.Paths.project_dir()).resolve()
KEY='_combat_skill_editor_delivery'

class Delivery:
    def __init__(self):
        self.handle=None
        self.api=None
        self.runner=None
        self.index=-1
        self.report={'status':'running','stages':[], 'scope':'Default four-hit chain, real combined damage and full 20-bout compatibility; current DLLs, original arena and original skill assets'}
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        self.path=ROOT/'Saved/Acceptance'/('SkillEditorCompatibility_'+stamp+'.json')
        self.stages=['default_chain_only.py','combined_sources.py','start_acceptance.py']

    def save(self):
        self.path.write_text(json.dumps(self.report,ensure_ascii=False,indent=2),encoding='utf-8')

    def tick(self,delta):
        if self.runner is not None and self.runner.handle is not None:
            return
        if self.runner is not None:
            self.report['stages'][-1].update(status=self.runner.report['status'],report=str(self.runner.path),assertions=len(self.runner.report.get('assertions',[])))
            self.runner=None
        self.index+=1
        if self.index>=len(self.stages):
            self.report['status']='passed' if all(s['status']=='passed' for s in self.report['stages']) else 'failed'
            u.unregister_slate_post_tick_callback(self.handle); self.handle=None; self.save(); return
        path=ROOT/'Tools/tests'/self.stages[self.index]
        self.api=runpy.run_path(str(path))
        self.api['start']()
        self.runner=getattr(builtins,['_combat_default_chain_only','_combat_combined_sources','_combat_arena_regression'][self.index])
        self.runner.report['release_provenance_from_coordinator']={'scope':'Skill editor compatibility regression','source':'current modified working tree; see DLL hashes','viewport':'fixed 1920x1080 render target; desktop window can be smaller'}
        self.report['stages'].append({'name':path.name,'status':'running','report':str(self.runner.path)})
        self.save()

def start():
    for key in (KEY,'_combat_arena_regression','_combat_combined_sources','_combat_skill_editor_regression'):
        if getattr(getattr(builtins,key,None),'handle',None) is not None:
            raise RuntimeError('Active runner: '+key)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    if not world or u.GameplayStatics.is_game_paused(world):
        raise RuntimeError('An unpaused original-arena PIE session is required')
    if not u.CombatSkillEditorLibrary.set_preview_resolution(1920,1080):
        raise RuntimeError('Could not set fixed 1080p render target')
    players=[a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CombatCharacter) if not a.get_editor_property('is_boss')]
    if len(players)!=1:
        raise RuntimeError('Expected one player')
    if any(tag_name(d.get_editor_property('skill_tag')).startswith('Combat.Skill.Editor.') for d in players[0].get_editor_property('skill_definitions')):
        raise RuntimeError('Use a fresh original-arena PIE session, not a designer preview')
    players[0].retry_encounter()
    runner=Delivery(); setattr(builtins,KEY,runner); runner.save()
    runner.handle=u.register_slate_post_tick_callback(runner.tick)
    return str(runner.path)

def tag_name(value):
    return str(value.get_editor_property('tag_name'))

def status():
    r=getattr(builtins,KEY,None)
    if not r:return {'status':'not_started'}
    result=dict(r.report)
    if r.runner:
        result['current']={'status':r.runner.report['status'],'assertions':len(r.runner.report.get('assertions',[])),'rounds':len(r.runner.report.get('rounds',[]))}
    result['path']=str(r.path)
    return result

def stop():
    r=getattr(builtins,KEY,None)
    if r and r.handle is not None:
        if r.api:r.api['stop']()
        u.unregister_slate_post_tick_callback(r.handle); r.handle=None
        if r.report['stages'] and r.runner:
            r.report['stages'][-1].update(status=r.runner.report['status'],assertions=len(r.runner.report.get('assertions',[])))
        r.report['status']='stopped';r.save()
    return status()
