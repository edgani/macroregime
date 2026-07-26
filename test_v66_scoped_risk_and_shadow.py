from __future__ import annotations
import hashlib,json,tempfile
from pathlib import Path
from us_equity_risk_cap_v66 import evaluate_monthly_risk_cap
from prospective_shadow_v66 import append_shadow_forecast,verify_shadow_ledger

def months(values):
    return [{"observed_month":f"2025-{i:02d}-01","close":v} for i,v in enumerate(values,1)]

def main():
    checks={}
    def ck(n,x): checks[n]=bool(x); assert x,n
    on=evaluate_monthly_risk_cap(months(range(100,112)),as_of="2025-12-20",max_staleness_months=0)
    ck('risk_on',on.status=='BASELINE_CAP_ALLOWED' and on.max_broad_us_equity_multiplier==1.0)
    off=evaluate_monthly_risk_cap(months([100,101,102,103,104,105,106,107,108,80]),as_of="2025-10-20",max_staleness_months=0)
    ck('risk_off',off.status=='REDUCE_TO_CASH_CAP' and off.max_broad_us_equity_multiplier==0.0)
    stale=evaluate_monthly_risk_cap(months(range(100,112)),as_of="2026-03-01",max_staleness_months=1)
    ck('stale_fail_closed',stale.status=='NO_PERMISSION_FAIL_CLOSED' and stale.max_broad_us_equity_multiplier==0.0)
    gap=months(range(100,110)); gap[-1]['observed_month']='2025-12-01'
    ck('gap_fail_closed',evaluate_monthly_risk_cap(gap,as_of='2025-12-20').status=='NO_PERMISSION_FAIL_CLOSED')
    ck('no_ticker_or_short',not on.ticker_permission and not on.short_permission and not on.crash_prediction_permission)
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'ledger.jsonl'; h='a'*64
        row=append_shadow_forecast(p,component_id='TEST',scope='US',instrument='XYZ',orientation='LONG',horizon_days=21,feature_snapshot_sha256=h,data_snapshot_sha256=h,code_sha256=h,created_at_utc='2026-07-26T00:00:00+00:00',forecast_id='fixed')
        ck('ledger_valid',verify_shadow_ledger(p)['valid'])
        try:
            append_shadow_forecast(p,component_id='TEST',scope='US',instrument='XYZ',orientation='LONG',horizon_days=21,feature_snapshot_sha256=h,data_snapshot_sha256=h,code_sha256=h,created_at_utc='2026-07-26T00:00:00+00:00',forecast_id='fixed')
            duplicate=False
        except ValueError: duplicate=True
        ck('duplicate_rejected',duplicate)
        rows=p.read_text().splitlines(); obj=json.loads(rows[0]); obj['instrument']='TAMPER'; p.write_text(json.dumps(obj)+'\n')
        ck('tamper_detected',not verify_shadow_ledger(p)['valid'])
        ck('zero_capital',row['capital_permission']=='SHADOW_ONLY_ZERO_CAPITAL')
    print(json.dumps({'passed':sum(checks.values()),'total':len(checks),'checks':checks},indent=2))
if __name__=='__main__':main()
