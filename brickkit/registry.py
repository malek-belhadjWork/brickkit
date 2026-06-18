"""Generic registry machinery for registry-kind bricks.

The ``Registry`` *class* is the only shared machinery — domain-agnostic, copied
into every client as part of brickkit. Each registry brick owns its OWN
``Registry()`` instance, local to its folder; there is no global plugin
namespace.

Plugins register on import: a brick's ``__init__`` explicitly imports its plugin
modules so the decorators fire and the available impls are deterministic and
visible. Each plugin should DEFER its heavy third-party import into the factory
body, so that importing the brick only registers names cheaply and an unselected
plugin's dependency is never required (a tesseract client never needs the cloud
SDK, even though ``cloud.py`` ships in its engines/ folder).
"""
from __future__ import annotations

from typing import Any, Callable


class Registry:
    """A name -> factory map plus a registration decorator.

    The ``interface`` string documents the callable shape every plugin must
    satisfy (e.g. ``"(image, params) -> (text, confidence)"``). It is advisory:
    it travels with the brick so the stable contract is self-describing.
    """

    def __init__(self, interface: str = "") -> None:
        self._factories: dict[str, Callable[..., Any]] = {}
        self.interface = interface

    def register(self, name: str) -> Callable[[Callable], Callable]:
        def deco(factory: Callable) -> Callable:
            if name in self._factories:
                raise ValueError(f"plugin {name!r} already registered")
            self._factories[name] = factory
            return factory

        return deco

    def create(self, name: str, params: dict | None = None) -> Any:
        """Build the selected plugin instance. The instance is itself callable
        and implements the brick's stable interface."""
        if name not in self._factories:
            raise KeyError(
                f"unknown plugin {name!r}; available: {self.names()}"
            )
        return self._factories[name](**(params or {}))

    def names(self) -> list[str]:
        return sorted(self._factories)


def build_plugin(brick_module: Any, config: Any) -> Any:
    """Build the selected plugin callable for a registry brick from its config.

    Used both when a registry brick runs standalone and when it is injected as a
    sub-brick into another brick (e.g. ocr into extract)."""
    return brick_module.REGISTRY.create(config.impl, dict(config.params))
