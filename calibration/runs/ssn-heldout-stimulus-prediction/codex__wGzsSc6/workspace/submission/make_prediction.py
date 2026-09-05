#!/usr/bin/env python3
"""Fit a stable spatial SSN to the training recording and predict eval_I."""
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
import torch

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = Path(__file__).resolve().parent
R = np.load(DATA / "train_r_obs.npy").astype(np.float64)
Itrain = np.load(DATA / "train_I.npy").astype(np.float64)
Ieval = np.load(DATA / "eval_I.npy").astype(np.float64)
xy = np.load(DATA / "xy.npy").astype(np.float64)
N, NE, dt, tau, k = 49, 29, 0.01, 0.5, 0.5
is_i = np.arange(N) >= NE
dxy = xy[:, None, :] - xy[None, :, :]
d2 = np.sum(dxy*dxy, axis=2)
block = 2*is_i[:, None].astype(int) + is_i[None, :].astype(int)
sign = np.where(is_i, -1.0, 1.0)[None, :]

def kernel_W(theta):
    amp = np.exp(theta[:4]); width = np.exp(theta[4:])
    W = amp[block] * np.exp(-d2/(2.0*width[block]**2)) * sign
    np.fill_diagonal(W, 0.0)
    return W

def simulate_sampled(W, drive):
    r = np.zeros(N); out = np.empty((N, 61)); q = 0
    for z in range(drive.shape[1]):
        if z % 200 == 0:
            out[:, q] = r; q += 1
        if z + 1 < drive.shape[1]:
            u = np.maximum(W @ r + drive[:, z], 0.0)
            r = np.maximum(r + (dt/tau)*(-r + k*u*u), 0.0)
            if (not np.all(np.isfinite(r))) or r.max() > 10:
                return None
    return out

def residual(theta):
    pred = simulate_sampled(kernel_W(theta), Itrain)
    if pred is None:
        return np.full(R.size, 10.0)
    return (pred-R).ravel()

# Four Dale blocks, each with a fitted positive strength and isotropic length scale.
x0 = np.log([2.0, .62, .41, .68, .62, .95, 1.47, 1.07])
lo = np.log([.001]*4 + [.25]*4); hi = np.log([3.0]*4 + [10.0]*4)
fit = least_squares(residual, x0, bounds=(lo, hi), max_nfev=70,
                    diff_step=.005, xtol=1e-8, ftol=1e-8, gtol=1e-8)
W0 = kernel_W(fit.x)

# Multiple-shooting refinement. Each noisy observation starts a 200-step exact
# Euler rollout; after four time constants, its initial noise has nearly vanished.
torch.set_num_threads(1)
torch.manual_seed(1)
Ib = np.stack([Itrain[:, j*200:(j+1)*200].T for j in range(60)])
x = torch.tensor(R[:, :-1].T, dtype=torch.float64)
y = torch.tensor(R[:, 1:].T, dtype=torch.float64)
inp = torch.tensor(Ib, dtype=torch.float64)
base = torch.tensor(W0, dtype=torch.float64)
pretype = torch.tensor(is_i.astype(int))
tsign = torch.tensor(sign, dtype=torch.float64)
offdiag = torch.tensor(1.0-np.eye(N), dtype=torch.float64)
# Only local edges receive unstructured corrections; long-range weights retain
# the fitted Gaussian prior, which prevents noise from creating dense tails.
local = torch.tensor((d2 <= 13.0).astype(np.float64), dtype=torch.float64)
gain = torch.nn.Parameter(torch.ones((N, 2), dtype=torch.float64))
delta = torch.nn.Parameter(torch.zeros((N, N), dtype=torch.float64))
opt = torch.optim.Adam([gain, delta], lr=.01)
for _ in range(600):
    opt.zero_grad()
    W = (base*gain[:, pretype] + delta*local)*offdiag
    r = x
    for q in range(200):
        u = torch.relu(r @ W.T + inp[:, q, :])
        r = torch.relu(r + (dt/tau)*(-r + k*u*u))
    loss = ((r-y)**2).mean() + .003*((gain-1)**2).mean() + .3*(delta*delta).mean()
    loss.backward()
    torch.nn.utils.clip_grad_norm_([gain, delta], 1.0)
    opt.step()
    # Project onto Dale signs and the required zero diagonal after each update.
    with torch.no_grad():
        gain.clamp_(0.0, 3.0)
        candidate = (base*gain[:, pretype] + delta*local)*offdiag
        candidate = tsign*torch.relu(tsign*candidate)
        delta.copy_((candidate-base*gain[:, pretype])*local)
W = ((base*gain[:, pretype] + delta*local)*offdiag).detach().numpy()

# Continuous held-out simulation from the shared zero initial state.
r = np.zeros(N); pred = np.empty((N, Ieval.shape[1]), dtype=np.float64)
for z in range(Ieval.shape[1]):
    pred[:, z] = r
    if z + 1 < Ieval.shape[1]:
        u = np.maximum(W @ r + Ieval[:, z], 0.0)
        r = np.maximum(r + (dt/tau)*(-r + k*u*u), 0.0)
        if (not np.all(np.isfinite(r))) or r.max() > 10.0:
            raise RuntimeError("held-out rollout became unstable")
np.save(OUT / "r_pred.npy", pred)
np.save(OUT / "W_est.npy", W)
print("kernel parameters:", np.exp(fit.x))
print("prediction min/max/mean:", pred.min(), pred.max(), pred.mean())
