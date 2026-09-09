import math
from defillama_adapter import pct_change_days, chain_snapshot
import pandas as pd

class Resp:
    def __init__(self, payload, code=200): self.payload=payload; self.status_code=code
    def json(self): return self.payload
class Session:
    def get(self,url,params=None,headers=None,timeout=None):
        if "historicalChainTvl" in url:
            return Resp([{"date":1,"tvl":100},{"date":604801,"tvl":120},{"date":1209601,"tvl":150}])
        if "stablecoincharts" in url:
            return Resp([{"date":1,"totalCirculatingUSD":{"peggedUSD":50}},{"date":604801,"totalCirculatingUSD":{"peggedUSD":60}},{"date":1209601,"totalCirculatingUSD":{"peggedUSD":70}}])
        if "overview/dexs" in url:
            return Resp({"total24h":25,"change_7d":50,"totalDataChart":[[1,10],[604801,20],[1209601,30]]})
        if "overview/fees" in url:
            return Resp({"total24h":5,"change_7d":20,"totalDataChart":[[1,2],[604801,3],[1209601,4]]})
        return Resp({},404)

def run():
    x=chain_snapshot("X",session=Session())
    assert math.isfinite(x["tvl"])
    assert x["ecosystem_confirmation_count"] >= 2
    assert x["source_quality"] == "HIGH"
    print("PASS test_defillama_adapter")

if __name__ == "__main__": run()
