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
3dcode push ./data --source you   # validate → hash → dedup-check → upload → register
```

`./data` may be a single project, or a folder of project subdirs — each is uploaded under
`<source>/<project>/`.

## Fingerprints (dedup)

Computed on your machine, light deps, no Blender/GPU:

- `code_hash` — sha256 of normalized code (exact-code dups)
- `geom_hash` — sampled GLB mesh signature (geometric dups) · needs `[dedup]`
- `phash` — perceptual hash of a render (visual dups) · needs `[dedup]`

## 3D code dialects

Each code type plugs in how to validate / find code / hash for that dialect:

- **Blender Python** (`.py`)
- **CAD** — CadQuery, FreeCAD
- **OpenSCAD** (`.scad`)
- **Shaders** — GLSL / OpenGL

…extensible: add a `threedcode/dialects/<name>.py` adapter.

## Status

v0.1 — `config` / `validate` / `push` working end-to-end to R2. Next: Supabase registry,
dedup index + `check`, admin `ingest`/`reject`, and the web review Inbox.
