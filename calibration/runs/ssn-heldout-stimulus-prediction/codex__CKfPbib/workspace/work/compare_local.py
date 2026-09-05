exec(open('/workspace/work/compare_models.py').read().split("q0=")[0])
q=np.load('/workspace/work/q_refit3.npy');B=make(q);pcol=np.load('/workspace/work/pcol.npy');g=np.load('/workspace/work/localgain_0.01.npy')
BE=B.copy();BE[:,typ]=0;BI=B.copy();BI[:,~typ]=0
WL=BE*(1+(g[:N,None]-1)*pcol[None,:])+BI*(1+(g[N:,None]-1)*pcol[None,:])
WG=make(q,np.load('/workspace/work/twogain_alt3_0.03.npy')); WQ=make(q)
for n,W in [('local',WL),('global',WG),('q',WQ)]:
 o,s=sim(W);np.save('/workspace/work/eval_'+n+'.npy',o);print(n,o.mean(),o.std(),o.max(),s)
A=np.load('/workspace/work/eval_local.npy')
for n in ['global','q']:
 Bx=np.load('/workspace/work/eval_'+n+'.npy');print('diff',n,np.sqrt(np.mean((A-Bx)**2))/Bx.std())
