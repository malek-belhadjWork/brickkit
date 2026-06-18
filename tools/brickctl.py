"""brickctl — the deployment CLI for the brick framework.

Implements the copy + versioning model:

    scaffold <client>            create a client project from the template
    sync <client> [--brick X]    copy brickkit + brick engines into the client,
                                 stamping versions + content hashes into manifest
    verify <client>              re-hash copied engines vs manifest (drift check)
    upgrade <client> --brick X   preserve config, replace engine X with latest,
                                 run config migrations, update manifest

Engines are COPIED read-only into each client. Copies are never edited in place;
`verify` proves it. This tool is part of the master repo, not a brick.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRICKKIT = ROOT / "brickkit"
BRICKS = ROOT / "bricks"
CLIENTS = ROOT / "clients"
TEMPLATE = ROOT / "templates" / "client"

_VERSION_RE = re.compile(r'^\s*VERSION\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)
_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")


# --- helpers ---------------------------------------------------------------

def read_version(pkg_dir: Path) -> str:
    """Parse the VERSION constant from a package's __init__.py without importing
    it (avoids pulling a brick's optional dependencies)."""
    init = pkg_dir / "__init__.py"
    m = _VERSION_RE.search(init.read_text(encoding="utf-8"))
    if not m:
        raise ValueError(f"no VERSION constant in {init}")
    return m.group(1)


def hash_dir(path: Path) -> dict[str, str]:
    import hashlib

    path = Path(path)
    out: dict[str, str] = {}
    for p in sorted(path.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        rel = p.relative_to(path).as_posix()
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def all_brick_names() -> list[str]:
    pyproject = ROOT / "pyproject.toml"
    if pyproject.exists():
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        names = data.get("tool", {}).get("brickkit", {}).get("bricks")
        if names:
            return [n for n in names if (BRICKS / n).is_dir()]
    return [p.name for p in sorted(BRICKS.iterdir()) if (p / "__init__.py").exists()]


def _set_readonly(path: Path) -> None:
    for p in path.rglob("*"):
        if p.is_file():
            try:
                os.chmod(p, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
            except OSError:
                pass  # best-effort; verify is the real enforcement


def _make_writable(path: Path) -> None:
    for p in path.rglob("*"):
        if p.is_file():
            try:
                os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
            except OSError:
                pass


def _copy_pkg(src: Path, dst: Path) -> None:
    if dst.exists():
        _make_writable(dst)
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=_IGNORE)


def load_manifest(client: Path) -> dict:
    mf = client / "manifest.json"
    if mf.exists():
        return json.loads(mf.read_text(encoding="utf-8"))
    return {"framework": {}, "bricks": {}}


def save_manifest(client: Path, manifest: dict) -> None:
    (client / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def client_dir(name: str) -> Path:
    # Accept a bare client name (under clients/) or an explicit path.
    p = Path(name)
    return p if p.exists() or p.is_absolute() else CLIENTS / name


# --- commands --------------------------------------------------------------

def cmd_scaffold(args) -> int:
    client = client_dir(args.client)
    if client.exists():
        print(f"error: {client} already exists", file=sys.stderr)
        return 1
    client.mkdir(parents=True)
    (client / "data" / "in").mkdir(parents=True)
    (client / "data" / "out").mkdir(parents=True)
    (client / "engines").mkdir()
    for item in TEMPLATE.iterdir():
        if item.is_file():
            text = item.read_text(encoding="utf-8").replace("{{CLIENT}}", client.name)
            (client / item.name).write_text(text, encoding="utf-8")
    save_manifest(client, {"framework": {}, "bricks": {}})
    print(f"scaffolded {client}")
    print("next: edit config.yaml, then `brickctl sync`")
    return 0


def cmd_sync(args) -> int:
    client = client_dir(args.client)
    if not client.exists():
        print(f"error: {client} does not exist (scaffold first)", file=sys.stderr)
        return 1
    engines = client / "engines"
    engines.mkdir(exist_ok=True)
    manifest = load_manifest(client)

    # framework
    dst = engines / "brickkit"
    _copy_pkg(BRICKKIT, dst)
    manifest["framework"] = {
        "version": read_version(BRICKKIT),
        "hashes": hash_dir(dst),
    }

    bricks = args.brick or all_brick_names()
    for name in bricks:
        src = BRICKS / name
        if not src.is_dir():
            print(f"error: unknown brick {name!r}", file=sys.stderr)
            return 1
        bdst = engines / name
        _copy_pkg(src, bdst)
        manifest["bricks"][name] = {
            "version": read_version(src),
            "hashes": hash_dir(bdst),
        }
        print(f"synced {name}@{manifest['bricks'][name]['version']}")

    save_manifest(client, manifest)
    _set_readonly(engines)
    print(f"framework@{manifest['framework']['version']} + "
          f"{len(bricks)} brick(s) -> {engines}")
    return 0


def cmd_verify(args) -> int:
    client = client_dir(args.client)
    manifest = load_manifest(client)
    engines = client / "engines"
    ok = True

    def check(label: str, recorded: dict, path: Path) -> None:
        nonlocal ok
        expected = recorded.get("hashes", {})
        actual = hash_dir(path) if path.exists() else {}
        modified = sorted(k for k in expected if expected.get(k) != actual.get(k))
        added = sorted(set(actual) - set(expected))
        if modified or added:
            ok = False
            for k in modified:
                print(f"  DRIFT  {label}/{k} (modified or missing)")
            for k in added:
                print(f"  DRIFT  {label}/{k} (added)")
        else:
            print(f"  OK     {label}@{recorded.get('version')}")

    check("brickkit", manifest.get("framework", {}), engines / "brickkit")
    for name, rec in manifest.get("bricks", {}).items():
        check(name, rec, engines / name)

    print("verify: clean" if ok else "verify: DRIFT DETECTED")
    return 0 if ok else 1


def _find_migration(brick: str, frm: str, to: str) -> Path | None:
    mig = BRICKS / brick / "migrations" / f"{frm}__{to}.py"
    return mig if mig.exists() else None


def cmd_upgrade(args) -> int:
    client = client_dir(args.client)
    manifest = load_manifest(client)
    name = args.brick
    if name not in manifest.get("bricks", {}):
        print(f"error: {name!r} not synced into {client}", file=sys.stderr)
        return 1

    old_version = manifest["bricks"][name]["version"]
    new_version = read_version(BRICKS / name)
    print(f"upgrade {name}: {old_version} -> {new_version}")

    # 1. preserve config (it lives in config/, untouched by engine replacement)
    cfg_path = client / "config" / f"{name}.yaml"

    # 2. replace engine folder with latest
    bdst = client / "engines" / name
    _make_writable(client / "engines")
    _copy_pkg(BRICKS / name, bdst)

    # 3. run config migration if the version step ships one
    mig = _find_migration(name, old_version, new_version)
    if mig and cfg_path.exists():
        import importlib.util

        import yaml

        spec = importlib.util.spec_from_file_location(f"_mig_{name}", mig)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        raw = mod.migrate(raw)
        cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
        print(f"  applied migration {mig.name}")
    elif old_version != new_version:
        print("  no migration needed (backward-compatible)")

    # 4. update manifest
    manifest["bricks"][name] = {"version": new_version, "hashes": hash_dir(bdst)}
    save_manifest(client, manifest)
    _set_readonly(client / "engines")
    print(f"  {name} now at {new_version}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="brickctl")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scaffold", help="create a client project")
    s.add_argument("client")
    s.set_defaults(func=cmd_scaffold)

    s = sub.add_parser("sync", help="copy framework + bricks into a client")
    s.add_argument("client")
    s.add_argument("--brick", action="append", help="brick name (repeatable)")
    s.set_defaults(func=cmd_sync)

    s = sub.add_parser("verify", help="detect in-place edits to copied engines")
    s.add_argument("client")
    s.set_defaults(func=cmd_verify)

    s = sub.add_parser("upgrade", help="replace one brick with the latest version")
    s.add_argument("client")
    s.add_argument("--brick", required=True)
    s.set_defaults(func=cmd_upgrade)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
