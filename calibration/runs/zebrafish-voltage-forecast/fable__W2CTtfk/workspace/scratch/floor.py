import numpy as np
v=np.load('/workspace/data/train_data.npy'); s=np.load('/workspace/data/train_stim.npy')
st=np.where(s>0)[0]; N=len(v)
def apd_of(seg):
    up=np.argmax(seg>0.5); after=np.where(seg[up:]<0.2)[0]; return up+(after[0] if len(after) else len(seg)-up)
bounds=[(st[i], st[i+1] if i+1<len(st) else N) for i in range(len(st))]
apd=np.array([apd_of(v[a:b]) for a,b in bounds])
H=4113
def template_pred(origin, apd_pred_fn):
    pred=np.zeros(H)
    hist_idx=[i for i,(a,b) in enumerate(bounds) if b<=origin]
    hapd=apd[hist_idx]
    prev=list(apd[[i for i,(a,b) in enumerate(bounds) if a<origin]])
    widx=[i for i,(a,b) in enumerate(bounds) if origin<=a<origin+H]
    for k,i in enumerate(widx):
        x=bounds[i][0]; ap=apd_pred_fn(prev, i)
        j=hist_idx[np.argmin(np.abs(hapd-ap))]; tmpl=v[bounds[j][0]:bounds[j][1]]
        end=bounds[widx[k+1]][0] if k+1<len(widx) else origin+H
        L=end-x; seg=tmpl[:L] if L<=len(tmpl) else np.concatenate([tmpl, np.full(L-len(tmpl), tmpl[-1])])
        pred[x-origin:end-origin]=seg; prev.append(apd[i])
    # before the first stim of the window: continue the last pre-origin beat
    i0=[i for i,(a,b) in enumerate(bounds) if a<origin][-1]; a=bounds[i0][0]; L=bounds[widx[0]][0]-origin
    seg=v[origin:origin+L]  # true continuation of the ongoing beat (small part; approximates known template)
    pred[:L]=seg
    return pred
def rmse(p,o): return np.sqrt(np.mean((p-v[o:o+H])**2))
fns={'oracle APD':lambda prev,i: apd[i], 'mean APD':lambda prev,i: np.mean(prev), 'AR1':lambda prev,i: 105.3-0.617*prev[-1],
     'AR2':lambda prev,i: 122.7-0.72*prev[-1]-0.165*prev[-2], 'last APD (persistence)':lambda prev,i: prev[-1]}
for name,fn in fns.items():
    r=[rmse(template_pred(o,fn),o) for o in (8227,10284,12341)]
    print(f'{name:24s}', np.round(r,4), 'mean', np.mean(r).round(4))
# how much does the RMSE fall if APD known with +-e ms noise?
rng=np.random.default_rng(0)
for e in (2,4,6,8):
    r=[rmse(template_pred(o,lambda prev,i: apd[i]+rng.normal(0,e)),o) for o in (8227,10284,12341)]
    print(f'oracle+noise sd {e} ms      ', np.round(r,4), 'mean', np.mean(r).round(4))
