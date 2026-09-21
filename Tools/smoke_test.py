import json
import unreal
assets = unreal.EditorAssetLibrary.list_assets('/Game', recursive=True)
assert assets, 'Project has no assets'
assert unreal.load_class(None, '/Script/GameplayAbilities.AbilitySystemComponent'), 'GAS class missing'
assert unreal.load_class(None, '/Script/MotionWarping.MotionWarpingComponent'), 'Motion warping class missing'
print(json.dumps({'smoke': 'pass', 'asset_count': len(assets), 'project': unreal.Paths.project_dir(), 'engine': unreal.SystemLibrary.get_engine_version()}))

