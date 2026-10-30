from __future__ import annotations

import json
import shutil
import subprocess


def main() -> None:
    executable = shutil.which("nvidia-smi")
    if executable is None:
        print(json.dumps({"status": "not_run", "reason": "nvidia-smi unavailable"}, indent=2))
        return
    inventory = subprocess.run(
        [executable, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    print(json.dumps({"status": "inventory_only", "gpu": inventory, "benchmark": "not_run"}, indent=2))


if __name__ == "__main__":
    main()

