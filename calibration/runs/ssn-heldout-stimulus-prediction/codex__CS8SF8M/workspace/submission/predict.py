#!/usr/bin/env python3
"""Reproduce r_pred.npy from fitted, structured SSN models.

The numerical values below are fitted model parameters (not fitted rate values).
They were obtained by minimizing a censored-Gaussian likelihood of
train_r_obs.npy under repeated forward simulations.  See methods.md.
"""
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = Path(__file__).resolve().parent

NE = 29
DT_OVER_TAU = 0.01 / 0.5

# log([J_EE,J_EI,J_IE,J_II,sigma_EE,sigma_EI,sigma_IE,sigma_II])
P_OLD_PLAIN = np.array([1.3415741372289025,-0.5063065210891389,-0.8191394584750533,-0.11657670105595475,-0.664932773406774,-0.04392071420808216,0.29542329012647817,-0.06501847580093745])
P_OLD_COL = np.array([4.13057202342663,0.5142664532312464,0.21029251178334962,0.4429037092469248,-1.110405085298209,-0.05318093263854898,0.13320429719040494,0.1611443278744683])
P_JOINT_PLAIN = np.array([2.2345122547175427,-0.6237676968184929,-0.7643975106028624,0.7094176106788543,-0.8381512501011708,-0.006705163753208107,0.26296862953717115,-0.3209566156600725])
P_JOINT_COL = np.array([5.0277437050421945,0.47870688866596567,0.062232850442463794,0.7622104762800603,-1.1938657196963884,-0.059383888761780634,0.05921389825864487,-0.24902928100834626])

# Shrunk row corrections: (incoming-E multiplier, incoming-I multiplier).
# Only neurons receiving a training drive above 0.30 were identifiable.
ROW_PLAIN = {
 8:(.9956449810,1.1823067163),10:(1.0786124174,1.7927174268),
 12:(.7255591477,.7243676701),13:(.6372816791,1.8078794460),
 20:(1.3175856899,.5385996202),28:(.9978854915,1.2666109229),
 31:(1.0849972606,1.6671969249),38:(1.1104785153,.8815878760),
 39:(.9254360618,1.0674357504),40:(.9970668102,1.0028634669),
 43:(.9733012984,1.3406688051),46:(1.2774428177,.9310399549),
}
ROW_COL = {
 8:(1.0002284416,1.0949944457),10:(.9948192184,1.8023901089),
 12:(.7324319159,.8247814782),13:(.6108747999,1.8403256475),
 20:(1.4937995482,.6214348235),28:(1.0005002356,1.1971148378),
 31:(1.0458171877,1.7197133020),38:(1.0892856975,.9035922486),
 39:(1.0002500313,1.0),40:(1.0053472536,.9938432497),
 43:(.9818222251,1.2654615975),46:(1.4167808437,1.0979964217),
}

def make_w(logp, xy, column_normalized=False):
    kinds = np.r_[np.zeros(NE, dtype=int), np.ones(20, dtype=int)]
    d2 = ((xy[:, None, :] - xy[None, :, :]) ** 2).sum(axis=2)
    J = np.exp(logp[:4]).reshape(2, 2)
    sig = np.exp(logp[4:]).reshape(2, 2)
    S = np.empty((49, 49), dtype=np.float64)
    for a in range(2):
        for b in range(2):
            ix = np.ix_(kinds == a, kinds == b)
            block = np.exp(-d2[ix] / (2.0 * sig[a, b] ** 2))
            if column_normalized:
                block = block / block.sum(axis=0, keepdims=True)
            S[ix] = block
    W = J[kinds[:, None], kinds[None, :]] * S
    W[:, NE:] *= -1.0
    np.fill_diagonal(W, 0.0)
    return W

def apply_rows(W, corrections):
    W = W.copy()
    for i, (ge, gi) in corrections.items():
        W[i, :NE] *= ge
        W[i, NE:] *= gi
    return W

def simulate(W, drive):
    r = np.zeros(49, dtype=np.float64)
    out = np.empty(drive.shape, dtype=np.float64)
    out[:, 0] = r
    for q in range(1, drive.shape[1]):
        total = W @ r + drive[:, q]
        target = 0.5 * np.maximum(total, 0.0) ** 2
        r += DT_OVER_TAU * (-r + target)
        np.maximum(r, 0.0, out=r)
        if not np.isfinite(r).all() or r.max() > 20.0:
            raise RuntimeError("unstable fitted model")
        out[:, q] = r
    return out

def main():
    xy = np.load(DATA / "xy.npy").astype(np.float64)
    drive = np.load(DATA / "eval_I.npy").astype(np.float64)
    specifications = [
        (P_OLD_PLAIN, False, ROW_PLAIN, .20),
        (P_OLD_COL, True, ROW_COL, .10),
        (P_JOINT_PLAIN, False, ROW_PLAIN, .50),
        (P_JOINT_COL, True, ROW_COL, .20),
    ]
    prediction = np.zeros_like(drive, dtype=np.float64)
    for p, normalized, row_factors, weight in specifications:
        W = apply_rows(make_w(p, xy, normalized), row_factors)
        prediction += weight * simulate(W, drive)
    if prediction.shape != (49, 12001) or not np.isfinite(prediction).all():
        raise RuntimeError("invalid prediction")
    np.maximum(prediction, 0.0, out=prediction)
    np.save(OUT / "r_pred.npy", prediction)
    print(f"saved {prediction.shape}; range=({prediction.min():.6g}, {prediction.max():.6g})")

if __name__ == "__main__":
    main()
