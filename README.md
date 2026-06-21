# 3dcode — 3DCodeVerse data toolkit

CLI to validate, fingerprint (dedup), and upload **(code → 3D)** projects to the
3DCodeVerse corpus. Contributors run `3dcode push` from their own machine; data goes
straight to a private staging bucket (Cloudflare R2), gets reviewed, then ingested to the
canonical store.

## What's a "project"

One independent asset = its **code** + reference images / text prompt / video / derived
renders+glb + a `meta.json`. A **source** folder holds many projects:

```
<source>/<project>/
  meta.json                 # auto-generated identity card (id, dialect, hashes, status, …)
  model.py                  # the code (the core artifact)
  renders/ Image_015.webp   # reference / rendered images
  prompt.txt                # text prompt
  *.glb                     # mesh
```

## Install

```bash
pipx install "git+https://github.com/gaoypeng/3dcode_toolkit"
# dedup fingerprints (geometry + perceptual hashing) are optional extras:
pipx install "3dcode[dedup] @ git+https://github.com/gaoypeng/3dcode_toolkit"
```

## Configure (once)

```bash
3dcode config set \
  --endpoint https://<ACCOUNT_ID>.r2.cloudflarestorage.com \
  --bucket 3dcodeverse \
  --access-key-id <YOUR_KEY> --secret-access-key <YOUR_SECRET> \
  --source yourname
```
Saved to `~/.config/3dcode/config.toml` (chmod 600). You can also use `R2_*` env vars.
**Never commit your filled-in config** — only `config.toml.example` (placeholders) is in the repo.

## Use

```bash
3dcode validate ./data            # layout + structure + anomaly checks, no upload
3dcode check ./data               # validate + flag duplicates vs the corpus, no upload
3dcode anomalies ./data           # distribution outliers (code length / char count)
3dcode exec ./data                # run the code locally; record pass/fail in meta.json
3dcode render ./data --mode white # render the code locally into renders/ (white | textured)
3dcode grid ./data                # contact-sheet PNG of all thumbnails (visual review)
3dcode push ./data --source you   # validate → hash → dedup-check → upload → register
```

### Executability (`3dcode exec`)

Runs each project's code **locally, in your own runtimes** (nothing is uploaded) and records
the result in `meta.json`. Pass = ran error-free **and** produced a non-empty mesh. Configure
the runtimes once:

```bash
3dcode config set --blender-5-0 /path/to/blender-5.0/blender \
                  --blender-5-1 /path/to/blender-5.1/blender
```
Blender Python is wired (runs in 5.0 + 5.1); CadQuery / FreeCAD / OpenSCAD adapters are next.
Missing runtimes are reported `n/a` (skipped, not failed). A maintainer may optionally re-run
`exec` on ingest as a backstop.

`./data` may be a single project, or a folder of project subdirs — each is uploaded under
`<source>/<project>/`.

## Fingerprints (dedup)

Computed on your machine, light deps, no Blender/GPU:

- `code_hash` — sha256 of normalized code (exact-code dups)
- `geom_hash` — sampled GLB mesh signature (geometric dups) · needs `[dedup]`
- `phash` — perceptual hash of a render (visual dups) · needs `[dedup]`

## 3D code dialects

Each code type plugs in how to validate / find code / hash for that dialect:

- **Blender Python** (`.py`) — exec runs in Blender 5.0 + 5.1; render = Workbench clay / EEVEE.
- **CadQuery** (`.py`, `--dialect cadquery`, install `3dcode[cadquery]`) — exec verifies a
  non-empty solid; render exports STL → clay-render in Blender.
- **FreeCAD / OpenSCAD / shaders** — adapters TBD.

…extensible: add a `threedcode/dialects/<name>.py` adapter (a `run()` for exec, `render()` for render).

## Admin (lab-side)

After reviewing uploads in the web Inbox (`/data/inbox`) and approving them:

```bash
3dcode config set --core-dir /path/to/canonical/store
3dcode ingest --all-approved      # pull approved R2 → core dir, mark ingested, clear staging
3dcode ingest <source>/<project>  # or a single project
```

## Status

`config` / `validate` / `check` / `anomalies` / `exec` / `push` / `ingest` working end-to-end:
contributor pushes → R2 staging + validation report in the registry → admin reviews in the
web Inbox → approve → `ingest` pulls to the canonical store. Next: R2 asset preview in the
Inbox, `3dcode render`, and CadQuery / FreeCAD exec adapters.
