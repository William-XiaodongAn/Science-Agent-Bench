"""Reproducible pipeline: fit W through the forward simulation on the training recording, then
simulate the held-out drive at full resolution. Usage: python3 make_submission.py <config-json>
Config keys: lam (float, ridge on log-deviations), free (bool), seeds (list), iters, cap, eval_guard, r0."""
import sys, json, time; from fit import *
cfg = dict(lam=0.3, free=True, seeds=[0], iters=200, cap=2.0, eval_guard=True, r0=0.01, sub=2)
if len(sys.argv) > 1: cfg.update(json.loads(sys.argv[1]))
print('config', cfg, flush=True)
t0 = time.time(); mask = make_mask(); preds = []; Ws = []
for sd in cfg['seeds']:
    m, h = fit(mask, lam=cfg['lam'], free_dev=cfg['free'], iters=cfg['iters'], eval_guard=cfg['eval_guard'], cap=cfg['cap'], seed=sd, sub=cfg['sub'], r0val=cfg['r0'])
    W = m().detach().numpy(); Ws.append(W)
    Re = simulate_np(W, I_ev, r0=np.full(N, cfg['r0']))
    ok = np.isfinite(Re).all() and Re.max() < 5.0
    print(f'seed {sd}: train nRMSE {nrmse(predict_obs(m, cfg["r0"]), r_obs, mask):.4f}  eval max {np.nanmax(Re):.3f} ok={ok}', flush=True)
    if ok: preds.append(Re)
R = np.mean(preds, 0) if preds else simulate_np(np.zeros((N,N)), I_ev)  # fallback: feedforward
R = np.clip(np.nan_to_num(R, nan=0.0, posinf=0.0), 0, None)
import os; os.makedirs('/workspace/submission', exist_ok=True)
np.save('/workspace/submission/r_pred.npy', R.astype(np.float64)); np.save('/workspace/submission/W_fit.npy', np.mean(Ws, 0))
print('wrote r_pred.npy', R.shape, 'max', R.max(), 'mean', R.mean(), f'{time.time()-t0:.0f}s')
