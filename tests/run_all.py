"""Run every tests/test_*.py module and report a combined result."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def main() -> None:
    total_pass = total_fail = 0
    for path in sorted(HERE.glob("test_*.py")):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        harness = getattr(module, "test", None)
        if harness is None:
            continue
        print(f"\n=== {path.name} ===")
        p, f = harness.run()
        total_pass += p
        total_fail += f
    print(f"\nTOTAL: {total_pass} passed, {total_fail} failed")
    sys.exit(1 if total_fail else 0)


if __name__ == "__main__":
    main()
