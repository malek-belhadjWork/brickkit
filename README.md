# brickkit — a reusable framework for modular "bricks"

A **brick** = a generic **engine** (core logic, never edited per client) + a
**config** (the only client/instance-specific surface). Every engine has the
shape `run(input, config) -> output`, so bricks compose into pipelines. The
framework is the deliverable; document extraction (invoices) is its first
instantiation, used to validate it.

See [`docs/CONVENTION.md`](docs/CONVENTION.md) for the full contract.

## Two kinds of brick
- **engine + config** — one engine, behavior driven entirely by config
  (`extract`, `validate`, `writeout`).
- **registry** — a stable interface + interchangeable plugins; config selects one
  via `impl` and passes its `params` (`source`, `ocr`). Adding an implementation
  is a new plugin file only — nothing downstream changes.

## Layout
```
brickkit/        the framework core (copied into every client)
bricks/          canonical engines, each with its own VERSION
  source/  (registry: folder | email | s3)
  ocr/     (registry: tesseract | synthetic | cloud)
  extract/ (engine: zonal OCR + reconciliation; locator strategy)
  validate/(engine: required + confidence + cross-field checks)
  writeout/(engine: destination + field->column mapping)
tools/brickctl.py   scaffold / sync / verify / upgrade CLI
tools/textgen.py    fixture generator (synthetic invoices)
templates/client/   client project skeleton
clients/            generated, self-contained client projects
docs/CONVENTION.md  the brick spec for onboarding a new brick
tests/              runnable proofs (no pytest needed)
```

## Deployment & versioning model
- Each client is a **self-contained project**; engine code is **copied in**
  (read-only) under `engines/`, stamped into `manifest.json` with content hashes.
- One `config.yaml` per client (one section per brick; omitted keys fall back to
  each brick's defaults). Different clients can run different engine versions.
- **Upgrade** = preserve config, replace the engine folder with the latest
  version, restore config. New config keys are optional (backward-compatible);
  only schema-changing versions ship a `migrations/<from>__<to>.py`.
- `brickctl verify` re-hashes copied engines vs the manifest to prove copies were
  never edited in place.

## CLI
```
python tools/brickctl.py scaffold <client>
python tools/brickctl.py sync     <client> [--brick extract ...]
python tools/brickctl.py verify   <client>
python tools/brickctl.py upgrade  <client> --brick extract
```

## Run the tests / the proof
```
python tests/run_all.py
```
The headline test, `tests/test_proof_ab.py`, builds two clients with **different
templates** (different field boxes, formats, mappings, destinations, page sizes)
and proves both work by editing **only config** — asserting the engine files are
**byte-identical** across `client_A` and `client_B`. Any engine edit needed for a
new client is a design leak.

## Resolution independence
Field boxes are **ratios (0..1)** of the page, so they locate the same region at
any DPI. The image is **not** resampled (resampling discards detail OCR needs);
the `canonical` long side is just the reference unit for margins, scaled to native
pixels per image. The `extract` `locator` is a strategy seam: `fixed` ships today;
an `anchor` locator (find a label, offset from it) can be added later so switching
a client to anchors becomes a config-only change.

## OCR note
`ocr` is a registry brick. Production selects a free engine (`tesseract`) by
config. The `synthetic` plugin is a dependency-free stand-in so the pipeline runs
offline in tests — swapping it for `tesseract` is a one-line config change, which
is the registry pattern's whole point.
