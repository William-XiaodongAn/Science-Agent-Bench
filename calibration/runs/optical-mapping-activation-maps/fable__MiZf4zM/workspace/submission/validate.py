#!/usr/bin/env python3
"""Reference-free validation of the submission maps (see methods.md, Validation performed)."""
import numpy as np
from scipy import ndimage as ndi
fn='/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat'
raw=np.fromfile(fn,dtype='<u2',offset=1024).reshape(-1,128*128+4)[:,:128*128].reshape(-1,128,128).transpose(0,2,1)[1:]
S=-raw.astype(np.float32); S=ndi.gaussian_filter(S,sigma=(3,1,1),mode='nearest')
m=np.load('/workspace/submission/mask.npy'); act=np.load('/workspace/submission/activation_ms.npy'); apd=np.load('/workspace/submission/apd80_ms.npy')
import json; on=json.load(open('/workspace/submission/run_stats.json'))['onsets']
yy,xx=np.mgrid[0:128,0:128]; core=m&(xx>=30)&(xx<=105)&(yy>=15)&(yy<=100)
# independent estimate: argmax dV/dt within window (heavier temporal smoothing to tame the plateau), mean over beats
dv=[]
for o in on:
    W=ndi.gaussian_filter1d(S[o-60:o+300],4,axis=0); d=np.diff(W,axis=0); dv.append(d.argmax(0)*1.89)
dv=np.mean(dv,0)
a=act[core]; b=dv[core]; a=a-np.median(a); b=b-np.median(b)
print('core: corr(act50, argmax dVdt)=%.4f, rms diff=%.2f ms, act50 spread (5-95)=%.1f ms'%(np.corrcoef(a,b)[0,1],np.sqrt(np.mean((a-b)**2)),np.diff(np.percentile(a,[5,95]))))
# beat-map consistency: per-beat rms deviation from mean map, core
import os
have=os.path.exists('/workspace/submission/diag_act_beats.npy')
if not have: print('per-beat arrays absent: run  python3 pipeline.py --diag  first for the per-beat consistency check')
ab=np.load('/workspace/submission/diag_act_beats.npy') if have else None; pb=np.load('/workspace/submission/diag_apd_beats.npy') if have else None
for i in (range(len(on)) if have else []):
    d=(ab[i]-act)[core]; d=d-np.nanmedian(d); dp=(pb[i]-apd)[core]
    print(f'beat {i:2d} onset {on[i]:5d}: act dev rms {np.sqrt(np.nanmean(d**2)):.2f} ms (median offset {np.nanmedian((ab[i]-act)[core]):+.2f}), apd dev rms {np.sqrt(np.nanmean(dp**2)):.2f}, apd median offset {np.nanmedian(dp):+.2f}')
# gradient sanity: activation pattern smoothness
gy,gx=np.gradient(np.where(m,act,np.nan)); g=np.hypot(gx,gy)[core]; print('core |grad act| median %.2f ms/px, 95%% %.2f'%(np.nanmedian(g),np.nanpercentile(g,95)))
print('apd core median %.1f, 5-95 %s'%(np.nanmedian(apd[core]),np.nanpercentile(apd[core],[5,95])))
