from __future__ import annotations
import numpy as np,pandas as pd
def benjamini_hochberg(pvalues,alpha=.05):
    p=np.asarray(pvalues,dtype=float);n=len(p)
    if n==0:return pd.DataFrame(columns=["p","q","reject"])
    order=np.argsort(p);sp=p[order];q=np.empty(n,float);prev=1.0
    for i in range(n-1,-1,-1):
        rank=i+1;val=min(prev,sp[i]*n/rank);q[i]=val;prev=val
    outq=np.empty(n,float);outq[order]=q
    return pd.DataFrame({"p":p,"q":outq,"reject":outq<=alpha})
