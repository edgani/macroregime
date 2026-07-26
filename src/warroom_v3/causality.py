from __future__ import annotations
from typing import Callable, Sequence, Any


def assert_prefix_invariant(fn: Callable[..., Sequence[Any]], args: tuple[Sequence[float],...], *, min_prefix: int) -> None:
    full=fn(*args)
    n=len(args[0])
    for end in range(min_prefix,n+1):
        prefix=fn(*(x[:end] for x in args))
        if prefix[-1] != full[end-1]:
            raise AssertionError(f"prefix invariance failed at {end}")


def assert_future_perturbation_invariant(fn: Callable[..., Sequence[Any]], args: tuple[list[float],...], *, cutoff: int, multiplier: float=7.0) -> None:
    base=fn(*args)
    changed=[]
    for series in args:
        altered=list(series)
        for i in range(cutoff+1,len(altered)):
            altered[i]=max(1e-9,altered[i]*multiplier)
        changed.append(altered)
    perturbed=fn(*tuple(changed))
    if base[:cutoff+1] != perturbed[:cutoff+1]:
        raise AssertionError("future perturbation changed past output")
