import numpy as np, time
dt=0.01; tau=0.5; k=0.5; a=dt/tau

def simulate(W, I, r0=None):
    """Forward Euler; I is (N,T). Returns r (N,T). Also returns u for adjoint."""
    N,T=I.shape
    r=np.zeros((N,T)); 
    if r0 is not None: r[:,0]=r0
    for t in range(T-1):
        u=W@r[:,t]+I[:,t]
        up=np.maximum(u,0)
        r[:,t+1]=(1-a)*r[:,t]+a*k*up*up
    return r

def loss_grad(W, I, obs_idx, Y, wts=None, r0=None, tobit_sigma=None):
    """L = sum_m wts_m * ||r[:,obs_idx[m]] - Y[:,m]||^2 ; returns L, dL/dW, r"""
    N,T=I.shape
    r=np.zeros((N,T)); U=np.zeros((N,T-1))
    if r0 is not None: r[:,0]=r0
    for t in range(T-1):
        u=W@r[:,t]+I[:,t]; U[:,t]=u
        up=np.maximum(u,0)
        r[:,t+1]=(1-a)*r[:,t]+a*k*up*up
    if wts is None: wts=np.ones(len(obs_idx))
    G=np.zeros((N,T)); res=r[:,obs_idx]-Y
    if tobit_sigma is None:
        G[:,obs_idx]=2*wts[None,:]*res
        L=float((wts[None,:]*res*res).sum())
    else:
        # censored-Gaussian likelihood (x 2 sigma^2): y>0 -> (r-y)^2 ; y==0 -> -2 s^2 log Phi(-r/s)
        from scipy.special import log_ndtr, ndtr
        s=tobit_sigma; P=r[:,obs_idx]; z=P/s; cens=(Y<=0)
        Lmat=np.where(cens, -2*s*s*log_ndtr(-z), res*res)
        phi=np.exp(-0.5*z*z)/np.sqrt(2*np.pi)
        Gmat=np.where(cens, 2*s*phi/np.maximum(ndtr(-z),1e-300), 2*res)
        G[:,obs_idx]=wts[None,:]*Gmat; L=float((wts[None,:]*Lmat).sum())
    lam=np.zeros(N); dW=np.zeros((N,N))
    for t in range(T-2,-1,-1):
        lam=(lam+G[:,t+1])  # lambda_{t+1} including direct obs term
        g=lam*(2*k*a*np.maximum(U[:,t],0))
        dW+=np.outer(g,r[:,t])
        lam=(1-a)*lam+W.T@g
    return L,dW,r

if __name__=='__main__':
    I=np.load('/workspace/data/train_I.npy').astype(float)
    Y=np.load('/workspace/data/train_r_obs.npy').astype(float)
    N=49; rng=np.random.default_rng(0)
    W=rng.normal(0,0.02,(N,N)); np.fill_diagonal(W,0)
    obs_idx=np.arange(0,12001,200)
    t0=time.time(); L,dW,r=loss_grad(W,I,obs_idx,Y); print('adjoint time',time.time()-t0, L)
    # finite-difference check
    eps=1e-5; i,j=3,40
    W2=W.copy(); W2[i,j]+=eps; L2,_,_=loss_grad(W2,I,obs_idx,Y)
    print('fd',(L2-L)/eps,'adj',dW[i,j])
    i,j=30,5
    W2=W.copy(); W2[i,j]+=eps; L2,_,_=loss_grad(W2,I,obs_idx,Y)
    print('fd',(L2-L)/eps,'adj',dW[i,j])
