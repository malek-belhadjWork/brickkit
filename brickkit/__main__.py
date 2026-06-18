"""Run a pipeline from a config file: ``python -m brickkit [config.yaml]``.

Defaults to ./config.yaml. Paths inside the config resolve against the current
working directory, so run this from your project's directory.
"""
from __future__ import annotations

import sys

from . import run_config


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    config_path = argv[0] if argv else "config.yaml"
    result = run_config(config_path)
    print(result)
    return result


if __name__ == "__main__":
    main()
