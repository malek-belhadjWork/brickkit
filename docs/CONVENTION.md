# The Brick Convention

A **brick** = a generic **engine** (core logic, never edited per client) + a
**config** (the only client/instance-specific surface). Every engine has the
shape `run(input, config) -> output` so bricks compose into pipelines.

This document is the contract. Following it lets you drop a brand-new brick into
any domain **without changing `brickkit/`**.

## A brick is a Python package exposing

| attribute      | meaning                                                        |
|----------------|----------------------------------------------------------------|
| `NAME: str`    | unique name; must match a config's `brick:` field              |
| `VERSION: str` | semver, **stamped in the brick** — the canonical version       |
| `KIND: str`    | `"engine"` or `"registry"`                                     |
| `CONFIG_MODEL` | a `pydantic` model (subclass of `BrickConfig`) for the payload |
| `run(data, config)` | the engine: `engine(input, config) -> output`             |

Engines are **pure with respect to client state**: every client-specific value
lives in `config`. No client name, path, or threshold is hardcoded.

## Two kinds

### Engine + config
One engine, behavior driven entirely by config.

```python
NAME, VERSION, KIND = "echo", "1.0.0", "engine"
class Config(BrickConfig):
    prefix: str = ""
CONFIG_MODEL = Config
def run(data, config):
    return f"{config.prefix}{data}"
```

### Registry
A stable interface + a registry of interchangeable plugins. Config selects one
via `impl` and passes its `params`. **Adding an implementation is a new plugin
file only** — the interface, the consumers, the pipeline, and other plugins are
untouched.

```
mybrick/
  __init__.py        # NAME/VERSION/KIND, REGISTRY = Registry(...), CONFIG_MODEL,
                     # explicit `from . import plugins`, run() that builds+calls
  plugins/
    __init__.py      # explicit `from . import a, b`  (registration on import)
    a.py             # @REGISTRY.register("a") def make_a(**params): ...
```

Rules that make the copy model work:
- Each registry brick owns its **own** `Registry()` instance (no global namespace).
- Plugins register on import; the brick imports them **explicitly** (no auto-scan).
- A plugin **defers its heavy third-party import into the factory body**, so an
  unselected plugin's dependency is never required even though its file ships in
  the client's `engines/` folder.

## Client config: one `config.yaml`, a section per brick

A client keeps a single `config.yaml`. `pipeline:` lists the stages; every other
top-level key is a brick section. **Registry** sections carry `impl` (+ optional
`params`); **engine** sections are the brick's settings directly (no wrapper).
Omitted keys fall back to the brick's model defaults, so a section is just the
client's overrides.

```yaml
pipeline: [source, extract, validate, writeout]
source:  {impl: folder, params: {path: ./data/in, glob: "*.png"}}   # registry
ocr:     {impl: tesseract}                                          # registry (rest = defaults)
extract:                                                            # engine: settings, flat
  canonical: {long_side_px: 1500}
  fields: [ ... ]
validate: { required: [...], min_confidence: 0.5, cross_checks: [...] }
writeout: { destination: ./data/out/results.csv, mapping: { ... } }
```

Unknown keys are **rejected** (typo guard). New **optional** keys (fields with
defaults) are the backward-compatible extension mechanism. `brickkit.load_bundle`
reads the file; `brickkit.validate_section` validates each section against its
brick's model.

(`brickkit.load_config` also loads a *single brick* from a standalone file with a
`brick:`/`version:`/`impl|settings:` envelope — handy for testing one brick in
isolation.)

## Composition & sub-bricks

Data between bricks is plain JSON-able dicts — bricks stay independent. A brick
that needs another brick that is *not* a pipeline stage (e.g. `extract` calling
`ocr` per crop) declares the injection:

```python
INJECTS = {"ocr": "ocr"}   # set config.ocr to the built plugin of brick "ocr"
```

`brickkit.pipeline.wire` builds the dependency's plugin from its config and binds
it onto the consumer's config attribute, so the consumer keeps the pure
`run(data, config)` shape and just calls `config.ocr(...)`.

## Deployment & versioning

- `brickkit` is a **pip-installable package** (framework + bundled bricks). A
  consuming project depends on it and provides only a `config.yaml`.
- Install privately from GitHub, pinned to a tag:
  `pip install "brickkit @ git+https://<token>@github.com/<you>/brickkit.git@v1.0.0"`.
- Different projects pin different versions → they can run different engine
  versions. Upgrade = bump the version pin and reinstall.
- New config keys are optional (backward-compatible); a schema-changing release
  bumps the major version.

## Adding / splitting a brick

A bundled brick is a subpackage of `brickkit.bricks` exposing NAME/VERSION/KIND.
`discover_bricks()` finds it automatically. To split a brick into its **own
package/repo** later, move the subpackage out and register it under the
`brickkit.bricks` entry-point group — discovery and configs are unchanged.
