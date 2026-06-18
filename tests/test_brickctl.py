"""Phase 1 proof: brickctl scaffolds, syncs, and detects drift."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from _harness import harness

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import brickctl  # noqa: E402

test = harness(__name__)
CLIENT = ROOT / "clients" / "_test_client"


def _cleanup():
    if CLIENT.exists():
        brickctl._make_writable(CLIENT)
        shutil.rmtree(CLIENT)


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


@test
def test_scaffold_sync_verify_and_drift():
    _cleanup()
    try:
        assert brickctl.cmd_scaffold(_Args(client="_test_client")) == 0
        assert (CLIENT / "main.py").exists()
        assert (CLIENT / "manifest.json").exists()

        # sync (no domain bricks exist yet -> copies brickkit only)
        assert brickctl.cmd_sync(_Args(client="_test_client", brick=None)) == 0
        assert (CLIENT / "engines" / "brickkit" / "brick.py").exists()

        # pristine copy verifies clean
        assert brickctl.cmd_verify(_Args(client="_test_client")) == 0

        # tamper with a copied engine file -> verify must fail
        tampered = CLIENT / "engines" / "brickkit" / "brick.py"
        brickctl._make_writable(CLIENT / "engines")
        tampered.write_text(
            tampered.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8"
        )
        assert brickctl.cmd_verify(_Args(client="_test_client")) == 1
    finally:
        _cleanup()


@test
def test_version_parsed_without_import():
    assert brickctl.read_version(ROOT / "brickkit") == "1.0.0"


if __name__ == "__main__":
    test.main()
