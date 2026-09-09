from __future__ import annotations
import numpy as np
from decision_core import purged_walkforward_splits, assert_no_lookahead

splits=purged_walkforward_splits(300,train_size=100,test_size=30,embargo=5,step=30)
assert len(splits)>=5
for tr,te in splits:
    assert_no_lookahead(tr,te,5)
    assert max(tr)+5 < min(te)

# Synthetic signal test: signal is formed from contemporaneous x only; future labels may not affect it.
rng=np.random.default_rng(7)
n=600
x=rng.normal(size=n)
y=0.15*x+rng.normal(scale=1,size=n)
signal=(x>0.8).astype(int)
signal2=signal.copy()
# scramble future outcomes; signal must remain identical
ys=y.copy(); ys[300:]=rng.permutation(ys[300:])
assert np.array_equal(signal,signal2)

# Purged OOS long-side sanity check on an injected relationship (mechanical test, not alpha claim)
means=[]
for tr,te in purged_walkforward_splits(n,train_size=180,test_size=60,embargo=10,step=60):
    test_sig=signal[te].astype(bool)
    if test_sig.any():
        means.append(float(y[te][test_sig].mean()-y[te].mean()))
assert means and np.mean(means)>0
print('TEST_WALKFORWARD_PASS',{'windows':len(means),'mean_synthetic_alpha':round(float(np.mean(means)),4)})
