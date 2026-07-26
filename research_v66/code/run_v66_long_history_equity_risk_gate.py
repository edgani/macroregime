from __future__ import annotations
import json, math, pathlib, datetime
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROTO = ROOT/'research_v66/protocols/V66_LONG_HISTORY_EQUITY_RISK_GATE_PROTOCOL_FROZEN.json'
OUT = ROOT/'research_v66/results/V66_LONG_HISTORY_EQUITY_RISK_GATE_RESULTS.json'
DATA = ROOT/'research_v66/data/sp500_monthly_shiller.csv'


def load_data() -> pd.DataFrame:
    d = pd.read_csv(DATA)
    d['Date'] = pd.to_datetime(d['Date'], errors='coerce')
    for c in ['SP500','Dividend']:
        d[c] = pd.to_numeric(d[c], errors='coerce')
    d = d.dropna(subset=['Date','SP500']).sort_values('Date').set_index('Date')
    # Newer source rows use zero placeholders for fundamentals; stop before first terminal zero-dividend block.
    d = d[(d['SP500'] > 0) & (d['Dividend'] > 0)].copy()
    d['ret'] = (d['SP500'] + d['Dividend']/12.0) / d['SP500'].shift(1) - 1.0
    d['sma10_signal'] = (d['SP500'].shift(1) > d['SP500'].shift(1).rolling(10).mean()).astype(float)
    tr12 = (1.0+d['ret']).rolling(12).apply(np.prod, raw=True)-1.0
    d['mom12_signal'] = (tr12.shift(1) > 0).astype(float)
    d['SMA10_LONG_CASH'] = d['sma10_signal']
    d['MOM12_LONG_CASH'] = d['mom12_signal']
    d['DUAL_AND_LONG_CASH'] = d[['sma10_signal','mom12_signal']].min(axis=1)
    d['DUAL_OR_LONG_CASH'] = d[['sma10_signal','mom12_signal']].max(axis=1)
    return d.dropna(subset=['ret']).copy()


def max_drawdown(x: np.ndarray) -> float:
    w = np.cumprod(1.0 + np.asarray(x, float))
    peak = np.maximum.accumulate(w)
    return float(np.min(w/peak - 1.0))


def es5(x: np.ndarray) -> float:
    x=np.asarray(x,float); k=max(1,int(math.ceil(.05*len(x))))
    return float(np.partition(x,k-1)[:k].mean())


def odds_ratio_loss5(signal: np.ndarray, ret: np.ndarray) -> float:
    # Haldane-Anscombe smoothing; risk-off=0, risk-on=1.
    off = signal < .5; on = ~off; event = ret <= -.05
    a=float(np.sum(event & off))+.5; b=float(np.sum((~event) & off))+.5
    c=float(np.sum(event & on))+.5; dd=float(np.sum((~event) & on))+.5
    return (a/b)/(c/dd)


def captures(g: np.ndarray, b: np.ndarray) -> tuple[float,float]:
    up=b>0; down=b<0
    return float(g[up].sum()/b[up].sum()), float(g[down].sum()/b[down].sum())


def build(d: pd.DataFrame, name: str, cost_bps: float, reverse: bool=False) -> pd.DataFrame:
    sig=d[name].astype(float).copy()
    if reverse: sig=1.0-sig
    turnover=sig.diff().abs().fillna(0.0)
    strat=sig*d['ret']-(cost_bps/10000.0)*turnover
    return pd.DataFrame({'benchmark':d['ret'],'signal':sig,'turnover':turnover,'strategy':strat}).dropna()


def bootstrap(x: pd.DataFrame, reps: int, block: int, seed: int, q: float) -> dict:
    arr=x[['benchmark','signal','strategy']].to_numpy(float); n=len(arr)
    rng=np.random.default_rng(seed); nb=math.ceil(n/block)
    es_imp=[]; dd_imp=[]; ors=[]
    chunk=200
    for off in range(0,reps,chunk):
        b=min(chunk,reps-off)
        starts=rng.integers(0,n,size=(b,nb))
        idx=np.concatenate([((starts[:,j,None]+np.arange(block)[None,:])%n) for j in range(nb)],axis=1)[:,:n]
        bench=arr[idx,0]; sig=arr[idx,1]; strat=arr[idx,2]
        k=max(1,int(math.ceil(.05*n)))
        bes=np.partition(bench,k-1,axis=1)[:,:k].mean(axis=1)
        ses=np.partition(strat,k-1,axis=1)[:,:k].mean(axis=1)
        es_imp.extend((ses-bes).tolist())
        bw=np.cumprod(1+bench,axis=1); sw=np.cumprod(1+strat,axis=1)
        bdd=np.min(bw/np.maximum.accumulate(bw,axis=1)-1,axis=1)
        sdd=np.min(sw/np.maximum.accumulate(sw,axis=1)-1,axis=1)
        dd_imp.extend((sdd-bdd).tolist())
        # odds ratio loops are cheap at 200x monthly n.
        for i in range(b): ors.append(odds_ratio_loss5(sig[i],bench[i]))
    es_imp=np.asarray(es_imp); dd_imp=np.asarray(dd_imp); ors=np.asarray(ors)
    return {
      'simultaneous_quantile':q,
      'es_improvement_lower':float(np.quantile(es_imp,q)),
      'es_improvement_probability_positive':float(np.mean(es_imp>0)),
      'drawdown_improvement_lower':float(np.quantile(dd_imp,q)),
      'drawdown_improvement_probability_positive':float(np.mean(dd_imp>0)),
      'loss5_odds_ratio_lower':float(np.quantile(ors,q)),
      'loss5_odds_ratio_median':float(np.median(ors))
    }


def evaluate(x: pd.DataFrame, start: str, end: str|None, proto: dict, seed: int) -> dict:
    z=x.loc[pd.Timestamp(start):(pd.Timestamp(end) if end else x.index.max())].copy()
    b=z.benchmark.to_numpy(); g=z.strategy.to_numpy(); s=z.signal.to_numpy()
    up,down=captures(g,b); bm=max_drawdown(b); gm=max_drawdown(g); be=es5(b); ge=es5(g)
    ann_b=float(np.mean(b)*12); ann_g=float(np.mean(g)*12)
    q=proto['cumulative_selection_correction']['family_alpha']/proto['cumulative_selection_correction']['total_family_size']
    boot=bootstrap(z,proto['bootstrap']['repetitions'],proto['bootstrap']['moving_block_months'],seed,q)
    gates={
      'return_shortfall':bool(ann_g-ann_b>=proto['gates']['annualized_return_shortfall_vs_benchmark_ge']),
      'mdd':bool(gm-bm>=proto['gates']['max_drawdown_improvement_ge']),
      'es':bool(ge-be>proto['gates']['expected_shortfall_5pct_improvement_gt']),
      'down_capture':bool(down<proto['gates']['downside_capture_lt']),
      'up_capture':bool(up>=proto['gates']['upside_capture_ge']),
      'boot_es_lower':bool(boot['es_improvement_lower']>proto['gates']['bootstrap_es_improvement_simultaneous_lower_gt']),
      'boot_dd_prob':bool(boot['drawdown_improvement_probability_positive']>=proto['gates']['bootstrap_drawdown_improvement_probability_ge']),
      'loss5_or_lower':bool(boot['loss5_odds_ratio_lower']>proto['gates']['risk_off_next_month_loss5_odds_ratio_simultaneous_lower_gt'])
    }
    return {
      'start':str(z.index.min().date()),'end':str(z.index.max().date()),'n_months':len(z),
      'benchmark_annualized_arithmetic':ann_b,'strategy_annualized_arithmetic':ann_g,'annualized_return_difference':ann_g-ann_b,
      'benchmark_max_drawdown':bm,'strategy_max_drawdown':gm,'drawdown_improvement':gm-bm,
      'benchmark_es5':be,'strategy_es5':ge,'es5_improvement':ge-be,
      'upside_capture':up,'downside_capture':down,'average_exposure':float(np.mean(s)),'average_monthly_turnover':float(z.turnover.mean()),
      'risk_off_next_month_loss5_odds_ratio':odds_ratio_loss5(s,b),'bootstrap':boot,'gates':gates,'pass':all(gates.values())
    }


def main():
    proto=json.loads(PROTO.read_text()); d=load_data(); results={}
    for j,name in enumerate(proto['candidates']):
        x=build(d,name,10); xs=build(d,name,25); xr=build(d,name,10,True)
        va=evaluate(x,*proto['splits']['validation'],proto,6610+j*10)
        lo=evaluate(x,proto['splits']['lockbox'][0],None,proto,6611+j*10)
        sv=evaluate(xs,*proto['splits']['validation'],proto,6612+j*10)
        sl=evaluate(xs,proto['splits']['lockbox'][0],None,proto,6613+j*10)
        rv=evaluate(xr,*proto['splits']['validation'],proto,6614+j*10)
        rl=evaluate(xr,proto['splits']['lockbox'][0],None,proto,6615+j*10)
        stress_ok=(sv['es5_improvement']>0 and sl['es5_improvement']>0)
        passed=va['pass'] and lo['pass'] and stress_ok and not(rv['pass'] and rl['pass'])
        results[name]={'validation':va,'lockbox':lo,'validation_25bps':sv,'lockbox_25bps':sl,
                       'reverse_validation':rv,'reverse_lockbox':rl,'stress_ok':stress_ok,'passed':bool(passed)}
    survivors=[k for k,v in results.items() if v['passed']]
    out={
      'schema':'warroom.v66.long_history_equity_risk_gate_results.v1',
      'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'protocol_sha256':proto['protocol_sha256'],
      'data_start':str(d.index.min().date()),'data_end':str(d.index.max().date()),'n_months':len(d),
      'results':results,'survivors':survivors,'survivor_count':len(survivors),
      'adjudication':{
        'passed':bool(survivors),
        'scoped_claim':'SUPPORTED' if survivors else 'NOT_PROVEN',
        'decision_permission':'REDUCE_US_BROAD_EQUITY_EXPOSURE_ONLY' if survivors else 'NONE',
        'capital_permission':'CONDITIONAL_RISK_CAP_ONLY' if survivors else 'BLOCKED',
        'ticker_permission':False,'short_permission':False,'may_increase_exposure':False
      },
      'claim_limit':proto['claim_limit']
    }
    OUT.write_text(json.dumps(out,indent=2,sort_keys=True))
    print(json.dumps({'survivors':survivors,'data_end':out['data_end'],
      'summary':{k:{'va_pass':v['validation']['pass'],'lo_pass':v['lockbox']['pass'],
                    'va_mdd_imp':v['validation']['drawdown_improvement'],'lo_mdd_imp':v['lockbox']['drawdown_improvement'],
                    'va_ret_diff':v['validation']['annualized_return_difference'],'lo_ret_diff':v['lockbox']['annualized_return_difference'],
                    'va_or_lb':v['validation']['bootstrap']['loss5_odds_ratio_lower'],'lo_or_lb':v['lockbox']['bootstrap']['loss5_odds_ratio_lower']}
                 for k,v in results.items()}},indent=2))

if __name__=='__main__': main()
