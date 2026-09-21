import sys,json,hashlib,datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools/python-libs'))
import numpy as np
import soundfile as sf
ROOT=Path('D:/UEproject/Combat');R=ROOT/'SourceAssets/Audio/Ready'
def db(x):return round(float(20*np.log10(max(float(x),1e-12))),3)
files=[]
for p in sorted(R.glob('*.wav')):
    info=sf.info(str(p));a,sr=sf.read(str(p),always_2d=True,dtype='float64');peak=float(np.max(np.abs(a)));rms=float(np.sqrt(np.mean(a*a)));frame_peak=np.max(abs(a),axis=1);audible=np.flatnonzero(frame_peak>10**(-60/20));clip_count=int(np.sum(abs(a)>=32767/32768));silent_fraction=float(np.mean(frame_peak<=10**(-60/20)))
    files.append({'file':str(p.relative_to(ROOT)).replace('\\','/'),'format':info.format,'subtype':info.subtype,'sample_rate_hz':sr,'channels':a.shape[1],'frames':len(a),'duration_seconds':round(len(a)/sr,6),'sample_peak_linear':peak,'sample_peak_dbfs':db(peak),'rms_linear':rms,'rms_dbfs':db(rms),'headroom_db':round(-db(peak),3),'full_scale_samples':clip_count,'is_digital_silence':bool(peak==0),'frames_below_minus60_dbfs_fraction':round(silent_fraction,6),'leading_below_minus60_dbfs_seconds':round(float(audible[0]/sr),6) if len(audible) else round(len(a)/sr,6),'trailing_below_minus60_dbfs_seconds':round(float((len(a)-1-audible[-1])/sr),6) if len(audible) else round(len(a)/sr,6),'clipping_risk':'No sampled full-scale clipping; downstream gain/summing still needs headroom' if not clip_count else 'Full-scale samples found','silence_risk':'Not silent' if rms>1e-5 else 'Very low RMS; inspect','sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
assert len(files)==13,len(files)
report={'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'All 13 game-ready WAV files; sample-level analysis, not an integrated loudness or true-peak certification','file_count':len(files),'all_pcm16_wave':all(x['format']=='WAV' and x['subtype']=='PCM_16' for x in files),'all_non_silent':all(not x['is_digital_silence'] for x in files),'total_full_scale_samples':sum(x['full_scale_samples'] for x in files),'minimum_headroom_db':min(x['headroom_db'] for x in files),'notes':['No source file has digital silence or sampled clipping.','Short sword whooshes are intentionally brief (about 0.1–0.16 s).','Metal clash tails are intentionally longer; avoid stacking many full-volume instances.','Battle music contains the source composition\'s audible loop pause; crossfade when looping.','Intersample true peak, perceptual loudness and actual UE mixer playback have not been measured here.'],'files':files}
(ROOT/'Docs/Assets/AudioValidation.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))
