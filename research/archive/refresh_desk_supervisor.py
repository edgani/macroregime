"""Hard-timeout supervisor for the background refresh worker."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from desk_runtime import LOCK_PATH, write_status, utc_now_iso


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--markets", required=True)
    parser.add_argument("--scope", choices=["fast", "full"], default="fast")
    parser.add_argument("--hard-timeout", type=int, default=120)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    command = [
        sys.executable,
        str(HERE / "refresh_desk_worker.py"),
        "--markets",
        args.markets,
        "--scope",
        args.scope,
    ]
    if args.force:
        command.append("--force")

    write_status(
        state="RUNNING",
        message=f"Refreshing {args.scope} universe in the background",
        scope=args.scope,
        markets=args.markets.split(","),
        hard_timeout_seconds=args.hard_timeout,
        started_at_utc=utc_now_iso(),
    )
    try:
        process = subprocess.run(
            command,
            cwd=HERE,
            env=os.environ.copy(),
            text=True,
            capture_output=True,
            timeout=args.hard_timeout,
        )
        if process.returncode == 0:
            write_status(
                state="SUCCESS",
                message=f"{args.scope.capitalize()} refresh completed",
                scope=args.scope,
                finished_at_utc=utc_now_iso(),
                stdout_tail=process.stdout[-2000:],
            )
            return 0
        write_status(
            state="FAILED",
            message=f"Refresh worker failed with exit code {process.returncode}",
            scope=args.scope,
            finished_at_utc=utc_now_iso(),
            stdout_tail=process.stdout[-2000:],
            stderr_tail=process.stderr[-4000:],
        )
        return process.returncode or 1
    except subprocess.TimeoutExpired as exc:
        write_status(
            state="TIMEOUT",
            message=f"Refresh stopped after the hard {args.hard_timeout}s timeout; last-known-good data remains active",
            scope=args.scope,
            finished_at_utc=utc_now_iso(),
            stdout_tail=(exc.stdout or "")[-2000:] if isinstance(exc.stdout, str) else "",
            stderr_tail=(exc.stderr or "")[-2000:] if isinstance(exc.stderr, str) else "",
        )
        return 124
    except Exception as exc:
        write_status(
            state="FAILED",
            message=f"{type(exc).__name__}: {exc}",
            scope=args.scope,
            finished_at_utc=utc_now_iso(),
        )
        return 1
    finally:
        try:
            LOCK_PATH.unlink(missing_ok=True)
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
