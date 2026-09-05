"""Score the configurations returned by the 5 searches (runs/seed*.json) at HELD-OUT origins the evaluator never used,
next to the portfolio's first member, to check that local refinement generalises beyond the 3 dev origins."""
import json, sys, glob, numpy as np
sys.path.insert(0, '/workspace/dev'); sys.path.insert(0, '/workspace/submission')
from harness import score
from portfolio import PORTFOLIO
HOLD = (5000, 6100, 7200, 9300, 11300)      # 4113-sample windows starting here; the model is trained on the data before each
def norm(c):
    c = dict(c)
    for k in ('layers', 'leak'):
        if isinstance(c.get(k), list): c[k] = tuple(c[k])
    if isinstance(c.get('feedback_clip'), list): c['feedback_clip'] = tuple(c['feedback_clip'])
    return c
rows = []
for f in sorted(glob.glob('/workspace/dev/runs/seed*.json')):
    rep = json.load(open(f)); sd = rep['seed']
    if rep.get('error'): print(f, 'ERROR', rep['error']); continue
    cfg = norm(rep['config'])
    r_ret = score([cfg], seeds=(sd,), origins=HOLD, verbose=False)[0]
    r_p0 = score([norm(PORTFOLIO[0])], seeds=(sd,), origins=HOLD, verbose=False)[0]
    r_p1 = score([norm(PORTFOLIO[1])], seeds=(sd,), origins=HOLD, verbose=False)[0]
    hist = rep['dev_history']; first30 = min(hist[:30]); allbest = min(hist)
    print(f"seed {sd}: dev best portfolio {first30:.4f} -> after refinement {allbest:.4f} | HOLDOUT returned {r_ret[1]:.4f} vs portfolio[0] {r_p0[1]:.4f} portfolio[1] {r_p1[1]:.4f} | n_eval {rep['n_evaluated']} {rep['elapsed_sec']}s unmetered {rep['unmetered_warmups']} evaluated {rep['returned_was_evaluated']}")
    rows.append((r_ret[1], r_p0[1], r_p1[1]))
rows = np.array(rows); print('mean holdout: returned %.4f portfolio0 %.4f portfolio1 %.4f' % tuple(rows.mean(0)))
