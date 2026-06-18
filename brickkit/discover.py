"""Brick discovery + a one-call config runner.

After ``pip install brickkit`` you don't import bricks by hand:

    from brickkit import run_config
    run_config("config.yaml")          # load -> discover -> wire -> run

Bricks are found two ways:
  * bundled  — every subpackage of ``brickkit.bricks`` exposing NAME/VERSION/KIND
  * external — any installed package that registers a ``brickkit.bricks`` entry
               point (so a brick split into its own package still drops in)
"""
from __future__ import annotations

import importlib
import pkgutil
from typing import Any

from .config import load_bundle, validate_section
from .pipeline import run_pipeline, wire


def discover_bricks() -> dict[str, Any]:
    """Return {brick NAME -> brick module} from bundled + entry-point bricks."""
    found: dict[str, Any] = {}

    # bundled bricks under brickkit.bricks
    from . import bricks as _bricks_pkg

    for info in pkgutil.iter_modules(_bricks_pkg.__path__):
        module = importlib.import_module(f"{_bricks_pkg.__name__}.{info.name}")
        if hasattr(module, "NAME"):
            found[module.NAME] = module

    # external bricks via entry points (group "brickkit.bricks")
    try:
        from importlib.metadata import entry_points

        for ep in entry_points(group="brickkit.bricks"):
            module = ep.load()
            found[getattr(module, "NAME", ep.name)] = module
    except Exception:
        pass  # no external bricks installed

    return found


def build(config_path):
    """Load a config bundle, validate each section against its discovered brick,
    wire sub-brick injections. Returns (bound_by_name, ordered_stage_list)."""
    bundle = load_bundle(config_path)
    bricks = discover_bricks()
    stage_names = bundle["pipeline"]
    brick_names = [k for k in bundle if k != "pipeline"]

    missing = [n for n in brick_names if n not in bricks]
    if missing:
        raise KeyError(f"config references unknown brick(s) {missing}; "
                       f"available: {sorted(bricks)}")

    modules = {n: bricks[n] for n in brick_names}
    configs = {n: validate_section(modules[n], bundle[n]) for n in brick_names}
    bound = wire(modules, configs)
    return bound, [bound[s] for s in stage_names]


def run_config(config_path, data=None):
    """Build and run the pipeline described by a single config.yaml.

    Paths inside the config (e.g. ``./data/in``) resolve relative to the current
    working directory, so run from your project's directory."""
    _bound, stages = build(config_path)
    return run_pipeline(stages, data)
