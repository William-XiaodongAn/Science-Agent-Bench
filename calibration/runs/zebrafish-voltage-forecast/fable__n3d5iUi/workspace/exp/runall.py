import sys, json; sys.path.insert(0,'/workspace/baseline')
import numpy as np, search_api
from multiprocessing import Pool
v=np.load('/workspace/data/train_data.npy'); s=np.load('/workspace/data/train_stim.npy')
def one(seed):
    rep=search_api.run_search('/workspace/submission/search.py', seed, v, s, budget=60, extra_paths=['/workspace','/workspace/submission'])
    return rep
if __name__=='__main__':
    seeds=[int(x) for x in sys.argv[1].split(',')]
    with Pool(min(4,len(seeds))) as p: reps=p.map(one, seeds)
    for rep in reps:
        print(f"seed {rep['seed']}: n={rep['n_evaluated']} t={rep['elapsed_sec']}s err={rep['error']} unmetered={rep['unmetered_warmups']} shadow={rep['framework_shadowed']} evaluated={rep.get('returned_was_evaluated')} dev_best={rep.get('dev_best')}")
        print('   cfg', json.dumps(rep['config']))
        print('   hist', rep['dev_history'])
    json.dump(reps, open(sys.argv[2] if len(sys.argv)>2 else 'reps.json','w'), indent=1, default=str)
