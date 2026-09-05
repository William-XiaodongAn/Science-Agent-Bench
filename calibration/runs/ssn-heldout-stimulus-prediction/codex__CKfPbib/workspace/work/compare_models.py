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
q0=np.array([2,.61597,.40716,.63598,.62286,.97403,1.50573,1.11749]);q1=np.load('/workspace/work/q_refit.npy')
models={'base':make(q0),'gain03':make(q0,np.load('/workspace/work/twogain_0.03.npy')),'gain01':make(q0,np.load('/workspace/work/twogain_0.01.npy')),'alt':make(q1,np.load('/workspace/work/twogain_alt_0.03.npy')),'qrefit':make(q1)}
O={}
for n,W in models.items():O[n],s=sim(W);print(n,'mean/std/max/stab',O[n].mean(),O[n].std(),O[n].max(),s)
for a in O:print(a,{b:round(np.sqrt(np.mean((O[a]-O[b])**2))/O[b].std(),3) for b in O if b!=a})
