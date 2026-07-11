"""validate_all.py — run the ENTIRE validation stack in one command.

  1. validation_plus.py     — statistical methods + negative/positive controls (validates the validator)
  2. validate_real.py       — factor + macro battery on the real bundled data (reconciles prior work)
  3. component_validation.py — every engine: runs/deterministic/no-lookahead/output-sane/formula/edge

    python validate_all.py
"""
import subprocess, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
for script in ["validation_plus.py", "validate_real.py", "component_validation.py", "composition_audit.py", "filter_validation.py", "gem_validation.py", "alpha_discovery_test.py"]:
    print("\n" + "#" * 90 + f"\n# {script}\n" + "#" * 90)
    subprocess.run([sys.executable, os.path.join(HERE, script)])
print("\n" + "=" * 90)
print("ALL VALIDATION LAYERS COMPLETE. Trade only signals that clear perm_p<0.05 AND DSR>=0.95")
print("AND survive Reality-Check/SPA AND validate on YOUR live + non-US feeds.")
