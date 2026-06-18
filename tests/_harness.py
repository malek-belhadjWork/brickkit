"""Tiny zero-dependency test harness (pytest is not installed).

Usage in a test module::

    from _harness import harness
    test = harness(__name__)

    @test
    def test_something():
        assert 1 + 1 == 2

    if __name__ == "__main__":
        test.main()

Or run everything: ``python tests/run_all.py``.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

# Make the master repo root importable (brickkit) and the demo bricks importable.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "demo_bricks"))


class _Harness:
    def __init__(self, module_name: str) -> None:
        self.module_name = module_name
        self.tests: list = []

    def __call__(self, fn):
        self.tests.append(fn)
        return fn

    def run(self) -> tuple[int, int]:
        passed = failed = 0
        for fn in self.tests:
            try:
                fn()
                print(f"  PASS  {self.module_name}.{fn.__name__}")
                passed += 1
            except Exception:
                print(f"  FAIL  {self.module_name}.{fn.__name__}")
                traceback.print_exc()
                failed += 1
        return passed, failed

    def main(self) -> None:
        passed, failed = self.run()
        print(f"\n{passed} passed, {failed} failed")
        sys.exit(1 if failed else 0)


def harness(module_name: str) -> _Harness:
    return _Harness(module_name)
