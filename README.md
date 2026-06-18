# brickkit — a reusable framework for modular "bricks"

A **brick** = a generic **engine** (core logic, never edited per project) + a
**config** (the only project-specific surface). Every engine has the shape
`run(input, config) -> output`, so bricks compose into pipelines. The framework
is the deliverable; document extraction (invoices) is its first instantiation.

It's a **pip-installable package**: install `brickkit`, write a `config.yaml`,
run it. No copying brick files into each project.

See [`docs/CONVENTION.md`](docs/CONVENTION.md) for the full brick contract.

## Install

```bash
# from a private GitHub repo (pin a tag)
pip install "brickkit @ git+https://<TOKEN>@github.com/<you>/brickkit.git@v1.0.0"

# local development (this repo)
pip install -e .
```
The `tesseract` OCR plugin also needs the **Tesseract binary** installed on the
machine (pip can't install it): https://github.com/UB-Mannheim/tesseract/wiki

## Use it

A project is just a `config.yaml` (+ your input files). Run it any of these ways:

```bash
python -m brickkit config.yaml          # no code needed
```
```python
from brickkit import run_config
run_config("config.yaml")               # one-liner in your own code
```
```python
# or use the pieces directly
from brickkit import discover_bricks, build, wire, run_pipeline
bound, stages = build("config.yaml")
```

## Two kinds of brick
- **engine + config** — one engine, behavior driven entirely by config
  (`extract`, `validate`, `writeout`).
- **registry** — a stable interface + interchangeable plugins; config selects one
  via `impl`, passes its `params` (`source`: folder/email/s3; `ocr`:
  tesseract/synthetic/cloud). Adding an implementation is a new plugin file only.

## The five document bricks (pipeline: source → extract → validate → writeout)
- **source** (registry) — fetch input files (`folder` handles PDFs and images).
- **ocr** (registry) — image crop → (text, confidence). Used *by* extract.
- **extract** (engine) — ratio boxes per field, crop at margins, call OCR,
  reconcile (format-match then highest confidence), cast types. Supports PDFs
  (rasterized) and per-field `page:` and `chars:` hints.
- **validate** (engine) — required fields + confidence + cross-field checks → flags.
- **writeout** (engine) — destination + field→column mapping (CSV).

## Layout
```
brickkit/
  __init__.py            framework API (+ discover_bricks, build, run_config)
  brick.py config.py pipeline.py registry.py version.py discover.py __main__.py
  bricks/                bundled bricks (discovered at runtime)
    source/ ocr/ extract/ validate/ writeout/
tools/
  textgen.py             fixture generator (synthetic invoices, tests)
  check_ocr.py           verify real Tesseract end-to-end
docs/CONVENTION.md       the brick spec (how to add a brick in any domain)
tests/                   runnable proofs — `python tests/run_all.py`
pyproject.toml           package metadata + brick entry points
```

## Config (one `config.yaml`, a section per brick)
```yaml
pipeline: [source, extract, validate, writeout]
source:  {impl: folder, params: {path: ./data/in, glob: ["*.pdf", "*.png"]}}
ocr:     {impl: tesseract, params: {cmd: "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"}}
extract:
  pdf_dpi: 200
  canonical: {long_side_px: 2200}
  fields:
    - {name: invoice_number, type: string, box: [0.75, 0.14, 0.18, 0.02], format: 'INV-\d+'}
    # money fields, cross-checks, per-field `page:` and `chars:` as needed
validate: {required: [invoice_number, total], cross_checks: [...]}
writeout: {destination: ./data/out/result.csv, mapping: {invoice_number: "Invoice #"}}
```
Keys you omit fall back to each brick's defaults. Boxes are **ratios (0–1)** of the
page, so the same config works across DPIs.

## Versioning & private distribution
- The package version (`pyproject.toml`) is the unit. Pin it per project
  (`brickkit @ git+...@v1.0.0`) — different projects can run different versions.
- Keep the GitHub repo **private**; only people with repo access (or a token) can
  `pip install`. Tag releases (`git tag v1.0.0`) for reproducible installs.

## Tests
```bash
python tests/run_all.py     # 17 tests, offline (uses the synthetic OCR stand-in)
```
The headline test (`tests/test_proof_ab.py`) runs two different invoice templates
through the **same installed package**, differing only in their `config.yaml`.
