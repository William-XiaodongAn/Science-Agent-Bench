import numpy as np
p='/workspace/data/';E=np.load(p+'eval_I.npy').astype(float);xy=np.load(p+'xy.npy');typ=np.arange(49)>=29;D2=((xy[:,None]-xy[None,:])**2).sum(2);N=49
def make(q,g=None):
 B=np.zeros((N,N))
 for a in range(2):
  for b in range(2):
   z=2*a+b;m=(typ[:,None]==a)&(typ[None,:]==b);B[m]=q[z]*np.exp(-D2[m]/(2*q[4+z]**2))*(-1 if b else 1)
 np.fill_diagonal(B,0)
 if g is None:return B
 return g[:N,None]*B*(~typ)[None,:]+g[N:,None]*B*typ[None,:]
def sim(W):
 r=np.zeros(N);o=np.zeros((N,12001));stab=-99
 for z in range(12000):
  x=W@r+E[:,z];r+=.02*(-r+.5*np.maximum(x,0)**2);r=np.maximum(r,0);o[:,z+1]=r
  if z%200==0:stab=max(stab,np.linalg.eigvals(np.diag(np.maximum(x,0))@W).real.max()-1)
 return o,stab
q3=np.load('/workspace/work/q_refit3.npy');q4=np.load('/workspace/work/q_refit4.npy')
models={'alt3':make(q3,np.load('/workspace/work/twogain_alt3_0.03.npy')),
'exp3':make(q3,np.load('/workspace/work/twogain_expected_0.03.npy')),
'q3':make(q3), 'q4':make(q4),
'round':make(np.array([.35,1,.4,.8,1.4,.8,1.6,1.1]))}
O={}
for n,W in models.items():O[n],ss=sim(W);print(n,'mean/std/max/stab',O[n].mean(),O[n].std(),O[n].max(),ss)
for a in O:print(a,{b:round(np.sqrt(np.mean((O[a]-O[b])**2))/O[b].std(),3) for b in O if b!=a})
