from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cusp_fragility_v73 import CuspEstimator, cusp_geometry, stable_roots, simultaneous_bootstrap_lower, gaussian_fit, gaussian_logpdf


def simulate_cusp(n=900, seed=73):
    rng=np.random.default_rng(seed)
    x1=rng.normal(size=n)
    x2=rng.normal(size=n)
    alpha=-0.15+0.9*x1
    beta=0.40+1.7*x2
    grid=np.linspace(-5,5,1601)
    dx=grid[1]-grid[0]
    z=np.empty(n)
    for i,(a,b) in enumerate(zip(alpha,beta)):
        lp=-0.25*grid**4+0.5*b*grid**2+a*grid
        p=np.exp(lp-lp.max()); p=p/p.sum()
        z[i]=rng.choice(grid,p=p)
    xa=np.column_stack([x1, rng.normal(size=n), rng.normal(size=n)])
    xb=np.column_stack([x2, rng.normal(size=n), rng.normal(size=n)])
    return z,xa,xb


def main():
    checks=[]
    def check(name, cond):
        checks.append((name,bool(cond)))
        if not cond: raise AssertionError(name)
    est=CuspEstimator(grid_points=401)
    z,xa,xb=simulate_cusp()
    fit=est.fit(z,xa,xb,starts=(0,1))
    a,b=est.alpha_beta(fit,xa,xb)
    geo=cusp_geometry(a,b,z)
    check('planted_fit_finite',np.isfinite(fit.nll))
    check('planted_beta_correlates_driver',abs(np.corrcoef(b,xb[:,0])[0,1])>0.45)
    check('geometry_finite',np.isfinite(geo).all())
    check('geometry_has_inside_states',geo[:,0].mean()>0.01)
    check('stable_roots_three',len(stable_roots(0.0,2.0))==2)
    # Null should not manufacture a large beta-driver relation.
    rng=np.random.default_rng(99)
    zn=rng.normal(size=900); xan=rng.normal(size=(900,3)); xbn=rng.normal(size=(900,3))
    tr=np.arange(0,650); te=np.arange(650,900)
    fn=est.fit(zn[tr],xan[tr],xbn[tr],starts=(0,1))
    check('null_fit_finite',np.isfinite(fn.nll))
    cusp_lp=est.score_samples(fn,zn[te],xan[te],xbn[te])
    gx=np.column_stack([xan,xbn])
    gc,gs=gaussian_fit(gx[tr],zn[tr])
    gauss_lp=gaussian_logpdf(gx[te],zn[te],gc,gs)
    check('null_no_holdout_density_advantage',float(np.mean(cusp_lp-gauss_lp))<0.03)
    d1=rng.normal(0.02,0.01,120); d2=rng.normal(0.03,0.01,120)
    boot=simultaneous_bootstrap_lower([d1,d2],resamples=300,block=12,seed=1)
    check('bootstrap_detects_planted_positive',min(boot['simultaneous_lower'])>0)
    d3=rng.normal(0,0.02,120)
    boot0=simultaneous_bootstrap_lower([d3],resamples=300,block=12,seed=2)
    check('bootstrap_rejects_null',boot0['simultaneous_lower'][0]<=0)
    out={'total':len(checks),'passed':sum(v for _,v in checks),'checks':[{'name':n,'pass':v} for n,v in checks]}
    Path('research_v57/results/V73_ENGINEERING_VALIDATION.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))

if __name__=='__main__': main()
