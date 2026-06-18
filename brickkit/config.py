"""Config envelope, base models, and the loader.

Every config file (any brick, any domain) shares one envelope:

    brick: <name>          # must match the brick's NAME
    version: "x.y.z"       # engine version this config targets (drives migration)
    # then, exactly one payload shape:
    impl: <plugin>         # registry bricks
    params: {...}          # registry bricks: plugin params
    settings: {...}        # engine bricks: engine settings

The framework owns the envelope; each brick owns its payload model
(``CONFIG_MODEL``) in its own folder, so the model travels with the engine when
copied into a client.

Unknown keys are rejected (typo guard). New *optional* keys (fields with
defaults) are the backward-compatible extension mechanism — adding one never
breaks an existing client config.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict


class BrickConfig(BaseModel):
    """Base for every brick config payload."""

    model_config = ConfigDict(extra="forbid")


class RegistryConfig(BrickConfig):
    """Base payload for registry bricks: pick a plugin and pass its params."""

    impl: str
    params: dict[str, Any] = {}


@dataclass
class Envelope:
    brick: str
    version: str | None
    payload: dict[str, Any]


def parse_envelope(raw: dict[str, Any], *, kind: str) -> Envelope:
    """Split a raw config dict into envelope fields + the brick's payload.

    For registry bricks the payload is ``{impl, params}``; for engine bricks it
    is the contents of ``settings``.
    """
    if "brick" not in raw:
        raise ValueError("config missing required 'brick' field")
    brick = raw["brick"]
    version = raw.get("version")

    if kind == "registry":
        if "impl" not in raw:
            raise ValueError(f"registry brick {brick!r} config missing 'impl'")
        payload = {"impl": raw["impl"], "params": raw.get("params", {})}
    else:  # engine
        payload = raw.get("settings", {})

    return Envelope(brick=brick, version=version, payload=payload)


def load_config(brick_module: Any, path: str | Path) -> BrickConfig:
    """Load + validate a config file against a brick's CONFIG_MODEL.

    Returns the validated payload model instance. Sub-brick injection (binding
    one brick into another) is handled separately by ``brickkit.pipeline.wire``.
    """
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: config must be a mapping")

    env = parse_envelope(raw, kind=brick_module.KIND)
    if env.brick != brick_module.NAME:
        raise ValueError(
            f"{path}: config brick {env.brick!r} != engine NAME "
            f"{brick_module.NAME!r}"
        )
    return brick_module.CONFIG_MODEL.model_validate(env.payload)


# --- single combined client config ----------------------------------------
# A client keeps ONE config.yaml with a section per brick, e.g.
#     pipeline: [source, extract, validate, writeout]
#     source: {impl: folder, params: {...}}     # registry section: impl + params
#     extract: {canonical: {...}, fields: [...]} # engine section: the settings, flat
# Omitted keys fall back to the brick's model defaults, so a section is just the
# client's overrides. No `brick:`/`version:`/`settings:` envelope — the section
# key already names the brick, and the brick's KIND says how to read the section.

def load_bundle(path: str | Path) -> dict[str, Any]:
    """Read the combined client config file into a dict (one key per brick, plus
    `pipeline`). Validation happens per section via :func:`validate_section`."""
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: config must be a mapping")
    if "pipeline" not in raw:
        raise ValueError(f"{path}: missing required 'pipeline' list")
    return raw


def validate_section(brick_module: Any, section: Any) -> BrickConfig:
    """Validate one brick's section from a combined config against its model.

    Registry sections carry `impl` (+ optional `params`); engine sections ARE the
    settings payload directly. Missing keys use the model's defaults."""
    section = section or {}
    if brick_module.KIND == "registry":
        if "impl" not in section:
            raise ValueError(f"brick {brick_module.NAME!r} section missing 'impl'")
        payload = {"impl": section["impl"], "params": section.get("params", {})}
    else:  # engine: the section is the settings payload
        payload = section
    return brick_module.CONFIG_MODEL.model_validate(payload)
