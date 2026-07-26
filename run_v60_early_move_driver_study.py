"""V60 early-move driver falsification study.

Frozen protocol: research_v60/protocols/V60_EARLY_MOVE_DRIVER_PROTOCOL_FROZEN.json
This is a historical data-ready battery only. It deliberately does not infer investor identity.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd

from parquet_compat import read_parquet_compat

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "research_v60" / "results"
LEDGER = ROOT / "research_v60" / "ledgers"
PROTOCOL = ROOT / "research_v60" / "protocols" / "V60_EARLY_MOVE_DRIVER_PROTOCOL_FROZEN.json"
Q = 0.05
RNG_SEED = 606025
BOOT = 600
BLOCK = 3


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _future_roll(x: pd.DataFrame, h: int, op: str) -> pd.DataFrame:
    shifted = x.shift(-1)
    rev = shifted.iloc[::-1]
    roll = rev.rolling(h, min_periods=h)
    ans = (roll.max() if op == "max" else roll.min()).iloc[::-1]
    return ans


def _slope(x: pd.DataFrame, win: int) -> pd.DataFrame:
    # Robust enough and vectorized: end-to-end average slope.
    return (x - x.shift(win - 1)) / max(win - 1, 1)


def _rank_panel(x: pd.DataFrame) -> pd.DataFrame:
    return x.rank(axis=1, pct=True, method="average")


def build_panels() -> tuple[dict[str, pd.DataFrame], dict[str, dict[str, pd.DataFrame]], pd.DataFrame, pd.DatetimeIndex]:
    sp = read_parquet_compat(ROOT / "research" / "sp500_panel.parquet").copy()
    sp["date"] = pd.to_datetime(sp["date"])
    panels = {
        k: sp.pivot(index="date", columns="Name", values=k).sort_index()
        for k in ("open", "high", "low", "close", "volume")
    }
    o, h, l, c, v = (panels[k].astype(float) for k in ("open", "high", "low", "close", "volume"))
    r = c.pct_change(fill_method=None)
    lr = np.log(c).diff()
    prev = c.shift(1)
    tr = pd.DataFrame(np.maximum.reduce([(h-l).values, (h-prev).abs().values, (l-prev).abs().values]), index=c.index, columns=c.columns)
    dollar = c * v
    market = r.median(axis=1)
    rel = r.sub(market, axis=0)

    # Corporate-action-like discontinuities. They are exclusion flags, never predictive features.
    overnight = o / prev - 1.0
    intraday = (h - l) / o.replace(0, np.nan)
    next_r = r.shift(-1)
    corp = (r.abs() >= 0.45) & (((r * next_r < 0) & (next_r.abs() >= 0.35)) | ((overnight.abs() >= 0.40) & (intraday <= 0.15)))
    past_corp = corp.rolling(252, min_periods=1).max().astype(bool)
    future_corp = _future_roll(corp.astype(float), 126, "max").fillna(0).astype(bool)
    valid = ~(past_corp | future_corp)

    f: Dict[str, pd.DataFrame] = {}
    for w in (5, 10, 21, 42, 63, 126, 252):
        f[f"ret_{w}"] = c.pct_change(w, fill_method=None)
    f["mom_252_21"] = c.shift(21) / c.shift(252) - 1.0
    for w in (21, 63, 126):
        f[f"relret_{w}"] = rel.rolling(w).sum()
    f["accel_5_21"] = f["ret_5"] - f["ret_21"]
    f["accel_21_63"] = f["ret_21"] - f["ret_63"]
    f["accel_63_126"] = f["ret_63"] - f["ret_126"]
    for w in (20, 63, 126, 252):
        f[f"dist_high_{w}"] = c / c.rolling(w).max() - 1.0
    for w in (20, 63):
        den = c.rolling(w).max() - c.rolling(w).min()
        f[f"range_loc_{w}"] = (c - c.rolling(w).min()) / den.replace(0, np.nan)
    for w in (10, 21, 63, 126):
        f[f"vol_{w}"] = lr.rolling(w).std()
    f["vol_ratio_21_126"] = f["vol_21"] / f["vol_126"]
    f["atr_14"] = tr.rolling(14).mean() / c
    f["atr_63"] = tr.rolling(63).mean() / c
    ma20 = c.rolling(20).mean(); sd20 = c.rolling(20).std()
    f["bb_width_20"] = 4 * sd20 / ma20
    f["compression_20_63"] = -((h.rolling(20).max()-l.rolling(20).min()) / (h.rolling(63).max()-l.rolling(63).min()).replace(0, np.nan))
    f["volume_ratio_5_20"] = v.rolling(5).mean() / v.rolling(20).mean()
    f["volume_ratio_20_63"] = v.rolling(20).mean() / v.rolling(63).mean()
    f["volume_ratio_63_252"] = v.rolling(63).mean() / v.rolling(252).mean()
    f["dollar_volume_ratio_20_63"] = dollar.rolling(20).mean() / dollar.rolling(63).mean()
    direction = np.sign(c.diff()).fillna(0)
    obv = (direction * v).cumsum()
    f["obv_slope_21"] = _slope(obv, 21) / v.rolling(21).mean().replace(0, np.nan)
    f["obv_slope_63"] = _slope(obv, 63) / v.rolling(63).mean().replace(0, np.nan)
    clv = ((c-l) - (h-c)) / (h-l).replace(0, np.nan)
    adl = (clv.fillna(0) * v).cumsum()
    f["adl_slope_21"] = _slope(adl, 21) / v.rolling(21).mean().replace(0, np.nan)
    f["adl_slope_63"] = _slope(adl, 63) / v.rolling(63).mean().replace(0, np.nan)
    mfv = clv * v
    f["cmf_20"] = mfv.rolling(20).sum() / v.rolling(20).sum().replace(0, np.nan)
    f["cmf_60"] = mfv.rolling(60).sum() / v.rolling(60).sum().replace(0, np.nan)
    f["up_volume_ratio_20"] = v.where(r > 0, 0).rolling(20).sum() / v.rolling(20).sum().replace(0, np.nan)
    f["price_volume_corr_20"] = r.rolling(20).corr(np.log1p(v).diff())
    f["amihud_21"] = (r.abs() / dollar.replace(0, np.nan)).rolling(21).mean()
    f["skew_63"] = lr.rolling(63).skew()
    f["maxret_21"] = r.rolling(21).max()
    f["gap_freq_21"] = (overnight.abs() > 0.02).rolling(21).mean()

    # Sample month-end only, after all features are formed.
    month_end = c.groupby(c.index.to_period("M")).tail(1).index
    features = {k: _rank_panel(x.loc[month_end].where(valid.loc[month_end])) for k, x in f.items()}

    targets: dict[str, dict[str, pd.DataFrame]] = {}
    specs = {"SURGE_21_20": (21, 0.20, "up"), "SURGE_63_30": (63, 0.30, "up"),
             "MONSTER_126_50": (126, 0.50, "up"), "DRAWDOWN_63_20": (63, -0.20, "down")}
    for name, (win, threshold, side) in specs.items():
        mx = _future_roll(c, win, "max") / c - 1.0
        mn = _future_roll(c, win, "min") / c - 1.0
        end = c.shift(-win) / c - 1.0
        event = (mx >= threshold) if side == "up" else (mn <= threshold)
        event = event.where(valid)
        targets[name] = {
            "event": event.loc[month_end], "endpoint": end.loc[month_end],
            "mfe": mx.loc[month_end], "mae": mn.loc[month_end],
        }
    return features, targets, valid.loc[month_end], month_end


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    a: str
    sa: int
    b: str | None = None
    sb: int = 1


def candidates(names: List[str]) -> List[Candidate]:
    out: List[Candidate] = []
    for a in names:
        for sa in (1, -1):
            out.append(Candidate(f"S:{a}:{sa:+d}", a, sa))
    for i, a in enumerate(names):
        for b in names[i+1:]:
            for sa in (1, -1):
                for sb in (1, -1):
                    out.append(Candidate(f"A:{a}:{sa:+d}&{b}:{sb:+d}", a, sa, b, sb))
    return out


def _candidate_indices(cands: List[Candidate], names: List[str]) -> tuple[np.ndarray,np.ndarray]:
    pos={n:i for i,n in enumerate(names)}
    # oriented columns: positive feature 0..F-1, inverse feature F..2F-1
    ia=[]; ib=[]
    F=len(names)
    for c in cands:
        ia.append(pos[c.a] if c.sa>0 else F+pos[c.a])
        if c.b is None: ib.append(-1)
        else: ib.append(pos[c.b] if c.sb>0 else F+pos[c.b])
    return np.asarray(ia,int),np.asarray(ib,int)


def _split_name(d: pd.Timestamp) -> str:
    if d <= pd.Timestamp("2015-12-31"): return "discovery"
    if d <= pd.Timestamp("2016-12-31"): return "validation"
    return "lockbox"


def simultaneous_penalty(matrix: np.ndarray, seed: int) -> float:
    if matrix.size == 0 or matrix.shape[1] < 4:
        return float("inf")
    means=np.nanmean(matrix,axis=1,keepdims=True)
    centered=np.nan_to_num(matrix-means,nan=0.0)
    rng=np.random.default_rng(seed)
    n=matrix.shape[1]
    maxima=np.empty(BOOT)
    starts=np.arange(n)
    for z in range(BOOT):
        idx=[]
        while len(idx)<n:
            st=int(rng.choice(starts)); idx.extend([(st+j)%n for j in range(BLOCK)])
        maxima[z]=np.max(centered[:,idx[:n]].mean(axis=1))
    return float(np.quantile(maxima,0.9875))


def main() -> int:
    protocol_hash=_sha(PROTOCOL)
    features, targets, valid, month_end=build_panels()
    names=sorted(features)
    cands=candidates(names)
    ia,ib=_candidate_indices(cands,names)
    nC=len(cands); target_names=list(targets); nT=len(target_names)
    split_dates={k:[] for k in ("discovery","validation","lockbox")}
    # Per target/split, list of monthly candidate metric vectors.
    metric_keys=["diff","recall","hits","selected_n","endpoint","baseline_endpoint","mfe","baseline_mfe","mae","baseline_mae","lift_diff"]
    store={(t,s,k):[] for t in target_names for s in split_dates for k in metric_keys}
    baseline_panel=features["mom_252_21"]
    F=len(names)
    BATCH=512

    for di,d in enumerate(month_end):
        split=_split_name(d)
        # Common feature-complete universe prevents candidate-specific missingness from becoming a hidden selector.
        fmat=np.column_stack([features[n].loc[d].to_numpy(float) for n in names])
        common=np.all(np.isfinite(fmat),axis=1) & np.isfinite(baseline_panel.loc[d].to_numpy(float))
        if common.sum()<60: continue
        base_scores=baseline_panel.loc[d].to_numpy(float)[common]
        X=fmat[common]
        Xo=np.concatenate([X,1.0-X],axis=1)
        ksel=max(1,int(math.ceil(Q*len(base_scores))))
        bidx=np.argpartition(base_scores,-ksel)[-ksel:]
        split_dates[split].append(str(d.date()))

        # Prepare target vectors once.
        tv={}
        for t in target_names:
            z=targets[t]
            tv[t]={kk:z[kk].loc[d].to_numpy(float)[common] for kk in ("event","endpoint","mfe","mae")}

        # Allocate monthly results, NaN when target unavailable.
        monthly={t:{k:np.full(nC,np.nan) for k in metric_keys} for t in target_names}
        for start in range(0,nC,BATCH):
            end=min(start+BATCH,nC); aa=ia[start:end]; bb=ib[start:end]
            S=Xo[:,aa].copy()
            pair=bb>=0
            if pair.any(): S[:,pair]=np.minimum(S[:,pair],Xo[:,bb[pair]])
            top=np.argpartition(S,-ksel,axis=0)[-ksel:,:]  # k x batch
            for t in target_names:
                y=tv[t]["event"]
                # Common target availability at this date; if path target is unavailable, skip whole month.
                if np.isfinite(y).sum()<len(y)*0.9: continue
                y=np.nan_to_num(y,nan=0.0)
                base_rate=float(y.mean()); bp=float(y[bidx].mean())
                sel_y=y[top]
                p=sel_y.mean(axis=0)
                monthly[t]["diff"][start:end]=p-bp
                monthly[t]["lift_diff"][start:end]=(p-bp)/base_rate if base_rate>0 else np.nan
                total=float(y.sum())
                monthly[t]["recall"][start:end]=sel_y.sum(axis=0)/total if total>0 else np.nan
                monthly[t]["hits"][start:end]=sel_y.sum(axis=0)
                monthly[t]["selected_n"][start:end]=ksel
                for key in ("endpoint","mfe","mae"):
                    arr=tv[t][key]
                    monthly[t][key][start:end]=np.nanmean(arr[top],axis=0)
                    monthly[t]["baseline_"+key][start:end]=float(np.nanmean(arr[bidx]))
        for t in target_names:
            for key in metric_keys: store[(t,split,key)].append(monthly[t][key])
        if di%6==0: print(f"month {d.date()} candidates={nC} universe={common.sum()}",flush=True)

    rows=[]
    for ci,c in enumerate(cands):
        for t in target_names:
            rec={"claim_id":f"{t}|{c.candidate_id}","target":t,"candidate_id":c.candidate_id,
                 "feature_a":c.a,"orientation_a":c.sa,"feature_b":c.b,"orientation_b":c.sb}
            for split in split_dates:
                for key in metric_keys:
                    arr=np.asarray([x[ci] for x in store[(t,split,key)]],float)
                    rec[f"{split}_{key}_mean"]=float(np.nanmean(arr)) if np.isfinite(arr).any() else np.nan
                    if key in ("hits","selected_n"): rec[f"{split}_{key}_sum"]=float(np.nansum(arr))
                rec[f"{split}_dates"]=int(np.isfinite(np.asarray([x[ci] for x in store[(t,split,'diff')]],float)).sum())
            rows.append(rec)
    df=pd.DataFrame(rows)

    penalties={}
    for ti,t in enumerate(target_names):
        mask=df.target.eq(t)
        for split in ("validation","lockbox"):
            raw=store[(t,split,"diff")]
            mat=np.vstack(raw).T if raw else np.empty((nC,0))
            good_cols=np.isfinite(mat).mean(axis=0)>0.9 if mat.size else np.array([],bool)
            mat=mat[:,good_cols] if mat.size else mat
            pen=simultaneous_penalty(mat,RNG_SEED+ti*10+(split=="lockbox"))
            penalties[f"{t}:{split}"]=pen
            df.loc[mask,f"{split}_simultaneous_lb"] = df.loc[mask,f"{split}_diff_mean"]-pen

    df["beats_baseline_return_both"]=(df.validation_endpoint_mean>=df.validation_baseline_endpoint_mean)&(df.lockbox_endpoint_mean>=df.lockbox_baseline_endpoint_mean)
    df["promoted"]=(df.validation_diff_mean>0)&(df.lockbox_diff_mean>0)&(df.validation_simultaneous_lb>0)&(df.lockbox_simultaneous_lb>0)&df.beats_baseline_return_both&(df.validation_hits_sum>=3)&(df.lockbox_hits_sum>=3)
    df["live_decision_weight"]=0.0; df["capital_permission"]="BLOCKED"
    df.sort_values(["promoted","lockbox_diff_mean","validation_diff_mean"],ascending=[False,False,False],inplace=True)
    OUT.mkdir(parents=True,exist_ok=True); LEDGER.mkdir(parents=True,exist_ok=True)
    df.to_csv(OUT/"V60_EARLY_MOVE_DRIVER_RESULTS.csv",index=False)
    df[["claim_id","target","candidate_id","promoted","validation_diff_mean","validation_simultaneous_lb","lockbox_diff_mean","lockbox_simultaneous_lb","live_decision_weight","capital_permission"]].to_csv(LEDGER/"V60_EARLY_MOVE_GLOBAL_TRIAL_LEDGER.csv",index=False)
    summary={"schema":"warroom.v60.early_move_driver_results","protocol_sha256":protocol_hash,
      "dataset_sha256":_sha(ROOT/"research"/"sp500_panel.parquet"),"base_feature_count":len(names),
      "candidate_count":nC,"target_count":nT,"total_claims":int(len(df)),"promoted_claims":int(df.promoted.sum()),
      "simultaneous_penalties":penalties,"split_dates":split_dates,"live_decision_weight":0.0,"capital_permission":"BLOCKED",
      "verdict":"PROVEN" if bool(df.promoted.any()) else "NO_DATA_READY_EARLY_MOVE_DRIVER_PROMOTED",
      "claim_boundary":"Historical US OHLCV panel only; no investor identity, derivatives, fundamentals, IHSG broker data or crypto liquidations are present.",
      "top_diagnostic_by_target":{}}
    for t in target_names:
        z=df[df.target.eq(t)].head(10)
        summary["top_diagnostic_by_target"][t]=z[["candidate_id","validation_diff_mean","validation_simultaneous_lb","lockbox_diff_mean","lockbox_simultaneous_lb","validation_hits_sum","lockbox_hits_sum","promoted"]].to_dict("records")
    (OUT/"V60_EARLY_MOVE_DRIVER_RESULTS.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps({k:summary[k] for k in ("base_feature_count","candidate_count","target_count","total_claims","promoted_claims","verdict")},indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
