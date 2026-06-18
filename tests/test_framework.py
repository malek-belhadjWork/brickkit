"""Phase 0 proof: the framework composes bricks with zero domain logic."""
from __future__ import annotations

from pathlib import Path

from _harness import harness

import echo
import textcase
from brickkit import (
    Registry,
    bind,
    build_plugin,
    hash_dir,
    load_config,
    run_pipeline,
    wire,
)
from brickkit.version import diff_hashes

test = harness(__name__)
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@test
def test_engine_brick_driven_by_config():
    cfg = load_config(echo, FIXTURES / "echo.yaml")
    assert echo.run("hello", cfg) == ">> hello"


@test
def test_registry_brick_selects_plugin():
    cfg = load_config(textcase, FIXTURES / "textcase.yaml")
    assert textcase.run("hello", cfg) == "HELLO"
    assert textcase.REGISTRY.names() == ["lower", "upper"]


@test
def test_pipeline_composes_both_kinds():
    bricks = {"echo": echo, "textcase": textcase}
    configs = {
        "echo": load_config(echo, FIXTURES / "echo.yaml"),
        "textcase": load_config(textcase, FIXTURES / "textcase.yaml"),
    }
    bound = wire(bricks, configs)
    out = run_pipeline([bound["echo"], bound["textcase"]], "hello")
    assert out == ">> HELLO", out


@test
def test_unknown_plugin_is_a_clear_error():
    reg = Registry()
    try:
        reg.create("nope")
    except KeyError as e:
        assert "nope" in str(e)
    else:
        raise AssertionError("expected KeyError for unknown plugin")


@test
def test_unknown_config_key_rejected():
    bad = FIXTURES / "_bad.yaml"
    bad.write_text("brick: echo\nsettings:\n  prefix: x\n  typo: 1\n", encoding="utf-8")
    try:
        load_config(echo, bad)
    except Exception as e:
        assert "typo" in str(e) or "extra" in str(e).lower()
    else:
        raise AssertionError("expected validation error for unknown key")
    finally:
        bad.unlink()


@test
def test_brick_mismatch_rejected():
    bad = FIXTURES / "_mismatch.yaml"
    bad.write_text("brick: not_echo\nsettings:\n  prefix: x\n", encoding="utf-8")
    try:
        load_config(echo, bad)
    except ValueError as e:
        assert "not_echo" in str(e)
    else:
        raise AssertionError("expected brick-name mismatch error")
    finally:
        bad.unlink()


@test
def test_hash_dir_detects_drift():
    root = Path(__file__).resolve().parent / "demo_bricks" / "echo"
    h1 = hash_dir(root)
    assert any(k.endswith("__init__.py") for k in h1)
    h2 = dict(h1)
    next_key = next(iter(h2))
    h2[next_key] = "deadbeef"
    diff = diff_hashes(h1, h2)
    assert diff["modified"] == [next_key]


if __name__ == "__main__":
    test.main()
