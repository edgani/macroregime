from __future__ import annotations
from dataclasses import dataclass
import subprocess, sys
from pathlib import Path

@dataclass(frozen=True)
class Check:
    name:str
    argv:tuple[str,...]

def run_checks(checks:list[Check], *, cwd:str|Path)->None:
    failures=[]
    for check in checks:
        p=subprocess.run(check.argv,cwd=str(cwd),capture_output=True,text=True,check=False)
        print(f"[{check.name}] rc={p.returncode}")
        if p.stdout.strip(): print(p.stdout.strip())
        if p.stderr.strip(): print(p.stderr.strip(),file=sys.stderr)
        if p.returncode: failures.append(check.name)
    if failures: raise SystemExit("validation failed: "+", ".join(failures))
