from pathlib import Path
import sys,json,hashlib,shutil,datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools/python-libs'))
import numpy as np
import soundfile as sf
ROOT=Path('D:/UEproject/Combat');R=ROOT/'SourceAssets/Audio/Ready';B=R.parent/'OriginalReady';B.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for p in R.glob('*.wav'):
    target=B/p.name
    if not target.exists():shutil.copy2(p,target)
results=[]
for p in sorted(R.glob('*.wav')):
    source=B/p.name;data,sr=sf.read(str(source),dtype='int16',always_2d=True);before_hash=sha(source)
    selected=p.stem.startswith(('SW_SwordSwing','SW_MetalClash','SW_Parry','SW_Dash','SW_Burst'))
    active=np.flatnonzero(np.max(abs(data.astype(np.int32)),axis=1)>32768*10**(-60/20))
    keep=round(sr*.002);cut=max(0,int(active[0])-keep) if selected and len(active) else 0
    if cut:
        output=data[cut:].copy();fade=min(round(sr*.0005),keep,len(output));output[:fade]=np.rint(output[:fade].astype(np.float64)*np.linspace(0,1,fade)[:,None]).astype(np.int16)
        sf.write(str(p),output,sr,subtype='PCM_16')
    else:
        # Restore identical original bytes for an idempotent rerun.
        if sha(p)!=before_hash:shutil.copy2(source,p)
    after,after_sr=sf.read(str(p),dtype='int16',always_2d=True)
    assert after_sr==sr and after.shape[1]==data.shape[1]
    assert int(np.max(abs(after.astype(np.int32))))<=int(np.max(abs(data.astype(np.int32))))
    results.append({'file':str(p.relative_to(ROOT)).replace('\\','/'),'original_file':str(source.relative_to(ROOT)).replace('\\','/'),'selected':selected,'trimmed_frames':cut,'trimmed_seconds':round(cut/sr,6),'preserved_pre_attack_seconds':.002 if cut else None,'fade_in_seconds':.0005 if cut else 0,'original_frames':len(data),'new_frames':len(after),'original_sha256':before_hash,'new_sha256':sha(p),'gain_increased':False,'music_unchanged':p.stem=='SW_BattleMusic' and sha(p)==before_hash})
report={'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'threshold_dbfs':-60,'retained_attack_lead_seconds':.002,'fade_seconds':.0005,'gain_policy':'No normalization or gain increase; only shorten lead and apply sub-millisecond fade within retained lead','unchanged':['SW_BattleMusic.wav','SW_Footstep.wav'],'files':results}
(ROOT/'Docs/Assets/AudioTrimReport.json').write_text(json.dumps(report,indent=2));print(json.dumps([{k:x[k] for k in ['file','trimmed_seconds','new_sha256']} for x in results],indent=2))
manifest=[]
for p in sorted(R.glob('*.wav')):
    a,s=sf.read(str(p));manifest.append({'file':p.name,'duration':round(len(a)/s,6),'sample_rate':s,'peak':float(np.max(abs(a))),'sha256':sha(p)})
(R.parent/'audio_manifest.json').write_text(json.dumps(manifest,indent=2))
