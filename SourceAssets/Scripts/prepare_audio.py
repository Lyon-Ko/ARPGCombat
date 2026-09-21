from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools/python-libs'))
import numpy as np
import soundfile as sf
R=Path(__file__).resolve().parents[1]/'Audio'; O=R/'Ready'; O.mkdir(exist_ok=True)
SR=48000
def read(p, speed=1):
    a,s=sf.read(str(p),always_2d=True); a=a.mean(axis=1)
    n=max(1,int(len(a)*SR/s/speed)); return np.interp(np.linspace(0,len(a)-1,n),np.arange(len(a)),a)
def save(name,a):
    a=a/max(1,np.max(abs(a))/0.88); sf.write(str(O/(name+'.wav')),a,SR,subtype='PCM_16')
def find(name): return next(p for p in R.rglob(name) if '__MACOSX' not in str(p))
for i in range(1,5):save('SW_SwordSwing_%02d'%i,read(find('swish-%d.wav'%(i+4)),1.05+i*.035))
for i in range(1,5):save('SW_MetalClash_%02d'%i,read(find('sword-knife-clash-%02d.wav'%(i*3))))
save('SW_Parry',read(find('sword-knife-clash-20.wav'),.84))
save('SW_Footstep',read(find('boots-leather-step-02.wav')))
dash=read(find('swish-13.wav'),.7); save('SW_Dash',dash)
a=read(find('impactMetal_heavy_000.ogg'),.8); b=read(find('swish-10.wav'),.7)
n=max(len(a),len(b))+int(SR*.6); mix=np.zeros(n); mix[:len(a)]+=a;mix[:len(b)]+=b*.6
t=np.arange(n)/SR;mix+=.24*np.sin(2*np.pi*(70*t-18*t*t))*np.exp(-5*t)
save('SW_Burst',mix)
music,sr=sf.read(str(R/'Downloads/the_final_battle.ogg'),always_2d=True)
sf.write(str(O/'SW_BattleMusic.wav'),music*.45,sr,subtype='PCM_16')
report=[]
for p in O.glob('*.wav'):
    a,s=sf.read(str(p));report.append({'file':p.name,'duration':round(len(a)/s,3),'sample_rate':s,'peak':float(np.max(abs(a))),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(R/'audio_manifest.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
