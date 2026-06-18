"""Composition: bind configs to bricks, inject sub-bricks, run a pipeline.

The pipeline threads ``output -> input`` down an ordered list of bricks. A brick
may depend on another brick that is NOT a pipeline stage (e.g. ``extract`` calls
``ocr`` per crop). Such dependencies are declared by the consumer brick and
injected into its config here, at wiring time — they never appear as stages.

A consumer brick declares injections with a module-level mapping::

    INJECTS = {"ocr": "ocr"}   # set config.ocr to the built plugin of brick "ocr"

The dependency must be a registry brick; its selected plugin (built from its own
config) is bound onto the named attribute of the consumer's config. The consumer
keeps the pure ``run(data, config)`` shape and calls ``config.ocr(...)``.
"""
from __future__ import annotations

from typing import Any

from .brick import BoundBrick
from .config import BrickConfig
from .registry import build_plugin


def bind(brick_module: Any, config: BrickConfig) -> BoundBrick:
    """Pair a brick with its (already validated + resolved) config."""
    return BoundBrick(brick_module, config)


def wire(
    brick_modules: dict[str, Any], configs: dict[str, BrickConfig]
) -> dict[str, BoundBrick]:
    """Build BoundBricks for every brick, injecting declared sub-bricks.

    Returns a name -> BoundBrick map. Note this includes non-stage bricks (like
    ``ocr``) so their plugins can be injected; the caller selects which bricks
    actually run, and in what order, via the pipeline's ``stages`` list.
    """
    bound: dict[str, BoundBrick] = {}
    for name, module in brick_modules.items():
        config = configs[name]
        injects: dict[str, str] = getattr(module, "INJECTS", {})
        for attr, dep_name in injects.items():
            dep_module = brick_modules[dep_name]
            dep_config = configs[dep_name]
            setattr(config, attr, build_plugin(dep_module, dep_config))
        bound[name] = BoundBrick(module, config)
    return bound


def run_pipeline(stages: list[BoundBrick], data: Any) -> Any:
    """Run an ordered list of bound bricks, threading output into input."""
    for brick in stages:
        data = brick.run(data)
    return data
