# {{CLIENT}} — a brick pipeline client

Self-contained project. **Edit only `config.yaml`.** The `engines/` folder is
copied from the master repo and is read-only — never edit it in place
(`brickctl verify` will catch drift).

- `engines/` — copied brick engines + `brickkit` (read-only)
- `config.yaml` — the only client-specific surface (one section per brick;
  omitted keys fall back to each brick's defaults)
- `data/in`, `data/out` — inputs (scans) and outputs (CSV)
- `manifest.json` — engine versions + content hashes copied in
- `main.py` — generic wiring; runs the pipeline

Run: `python main.py`
