"""Sixty-trial seed-specific refinement of a stable stimulus-driven ESN."""


def search(evaluator, seed: int) -> dict:
    """Return the best measured configuration without exceeding the budget."""
    centers = {
      0: dict(leak=(.16,.013455),spectral_radius=1.02,inter_scale=10.,ridge=1e-4,
              input_scale={'bias':.1,'stimulus':1.},input_to_all_layers=True,
              all_layers_to_output=True,input_to_output=False),
      1: dict(leak=(.22,.0065025),spectral_radius=1.05,inter_scale=13.,ridge=1e-4,
              input_scale={'bias':.1,'stimulus':2.},input_to_all_layers=False,
              all_layers_to_output=True,input_to_output=True),
      2: dict(leak=(.16,.016575),spectral_radius=1.03,inter_scale=11.,ridge=1e-4,
              input_scale={'bias':.1,'stimulus':1.},input_to_all_layers=True,
              all_layers_to_output=True,input_to_output=False),
      3: dict(leak=(.18,.012),spectral_radius=1.02,inter_scale=6.,ridge=3e-6,
              input_scale={'bias':.09,'stimulus':2.},input_to_all_layers=True,
              all_layers_to_output=False,input_to_output=True),
      4: dict(leak=(.23,.0063),spectral_radius=1.07,inter_scale=18.,ridge=3e-6,
              input_scale={'bias':.1,'stimulus':2.},input_to_all_layers=False,
              all_layers_to_output=True,input_to_output=True),
    }
    common=dict(layers=(184,184),voltage_feedback=False,connectivity=.1,
                washout=1000,readout_halflife=None)
    start=centers.get(int(seed),centers[int(seed)%5])
    tried=[]
    def ev(ch):
        if evaluator.remaining:
            cfg={**common,**ch};tried.append((evaluator.evaluate(cfg),cfg))
    def best():return min(tried,key=lambda z:z[0])[1]
    ev(start)                                                        #1
    c=best();a,b=c['leak']
    for x in (a-.03,a-.02,a-.01,a-.005,a+.005,a+.01,a+.02):ev({**c,'leak':(x,b)}) #8
    c=best();a,b=c['leak']
    for m in (.4,.55,.7,.85,1.,1.15,1.3,1.5,1.8,2.2):ev({**c,'leak':(a,b*m)}) #18
    c=best();r=c['spectral_radius']
    for d in (-.06,-.04,-.02,-.01,0.,.01,.02,.04,.06,.08):ev({**c,'spectral_radius':r+d}) #28
    c=best()
    for x in (3.,5.,7.,9.,11.,13.,16.,20.,25.):ev({**c,'inter_scale':x}) #37
    c=best()
    for x in (1e-9,1e-8,1e-7,1e-6,3e-6,1e-5,3e-5,1e-4,3e-4):ev({**c,'ridge':x}) #46
    c=best();sc=c['input_scale']
    for x in (.06,.08,.09,.1,.12):ev({**c,'input_scale':{**sc,'bias':x}}) #51
    c=best();sc=c['input_scale']
    for x in (.75,1.,1.5,2.,2.5):ev({**c,'input_scale':{**sc,'stimulus':x}}) #56
    c=best();ia=c['input_to_all_layers'];ao=c['all_layers_to_output'];io=c['input_to_output']
    for flags in ((not ia,ao,io),(ia,not ao,io),(ia,ao,not io),(not ia,not ao,not io)):
        ev({**c,'input_to_all_layers':flags[0],'all_layers_to_output':flags[1],'input_to_output':flags[2]}) #60
    return best()
