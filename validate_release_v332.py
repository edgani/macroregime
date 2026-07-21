"""Compatibility entry point for the v3.3.2 release verifier.

The exhaustive release evidence is frozen in V332_MASTER_RELEASE_REPORT.json.
This command runs the fast machine-specific verifier used by CHECK_EVERYTHING.bat.
"""
from validate_user_v332 import main

if __name__ == "__main__":
    main()
