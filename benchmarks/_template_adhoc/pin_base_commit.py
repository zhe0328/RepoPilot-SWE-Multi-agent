#!/usr/bin/env python3
"""Set config.yaml base_commit to current HEAD (buggy fixture snapshot)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

TASK_DIR = Path(__file__).resolve().parent
CONFIG = TASK_DIR / "config.yaml"


def main() -> None:
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=TASK_DIR.parents[1],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    text = CONFIG.read_text()
    updated, n = re.subn(
        r'^(\s*base_commit:\s*).*$',
        rf'\1"{sha}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if n != 1:
        raise SystemExit(f"Could not update base_commit in {CONFIG}")
    CONFIG.write_text(updated)
    print(f"Pinned base_commit to {sha} in {CONFIG.name}")


if __name__ == "__main__":
    main()
