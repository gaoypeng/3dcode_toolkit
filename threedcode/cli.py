"""`3dcode` CLI — contributor-side commands to validate and upload (code -> 3D) projects.

    3dcode config set --endpoint ... --access-key-id ... --secret-access-key ...
    3dcode validate ./data
    3dcode push ./data --source yourname
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from . import __version__
from .config import load_config, save_config
from .hashing import project_hashes
from .schema import META_NAME, find_projects, validate_project

app = typer.Typer(add_completion=False, help="3DCodeVerse data toolkit.")
config_app = typer.Typer(help="Manage R2 endpoint / token / default source.")
app.add_typer(config_app, name="config")


@app.command()
def version():
    """Print the toolkit version."""
    typer.echo(f"3dcode {__version__}")


@config_app.command("set")
def config_set(
    endpoint: str = typer.Option(None),
    bucket: str = typer.Option(None),
    access_key_id: str = typer.Option(None),
    secret_access_key: str = typer.Option(None),
    source: str = typer.Option(None, help="default source folder for your uploads"),
):
    """Write R2 settings to ~/.config/3dcode/config.toml (chmod 600)."""
    path = save_config({
        "endpoint": endpoint, "bucket": bucket, "access_key_id": access_key_id,
        "secret_access_key": secret_access_key, "source": source,
    })
    typer.echo(f"saved -> {path}")


@config_app.command("show")
def config_show():
    """Show the active config (secret masked)."""
    c = load_config()
    secret = (c.secret_access_key[:4] + "…") if c.secret_access_key else "(unset)"
    for k, v in {"endpoint": c.endpoint, "bucket": c.bucket,
                 "access_key_id": c.access_key_id or "(unset)",
                 "secret_access_key": secret, "source": c.source or "(unset)"}.items():
        typer.echo(f"  {k:18} {v}")


def _iter(root: Path, source: str):
    projects = find_projects(root)
    if not projects:
        typer.echo(f"no projects found under {root}", err=True)
        raise typer.Exit(1)
    for d in projects:
        errors, warnings, meta = validate_project(d, source)
        yield d, errors, warnings, meta


@app.command()
def validate(path: Path = typer.Argument(..., exists=True),
             source: str = typer.Option(None, help="source name (defaults to config)")):
    """Validate project(s) locally — no upload."""
    source = source or load_config().source or "unknown"
    bad = 0
    for d, errors, warnings, _ in _iter(path, source):
        if errors:
            bad += 1
            typer.secho(f"✗ {d.name}: {'; '.join(errors)}", fg="red")
        else:
            tag = typer.style("✓", fg="green")
            typer.echo(f"{tag} {d.name}" + (f"  ⚠ {'; '.join(warnings)}" if warnings else ""))
    if bad:
        raise typer.Exit(1)


@app.command()
def push(path: Path = typer.Argument(..., exists=True),
         source: str = typer.Option(None, help="source name (defaults to config)"),
         owner: str = typer.Option(None, help="who is responsible for this data"),
         dialect: str = typer.Option(None, help="override code dialect"),
         dry_run: bool = typer.Option(False, "--dry-run", help="validate + hash, do not upload")):
    """Validate -> hash -> write meta.json -> upload each project to R2 staging."""
    cfg = load_config()
    source = source or cfg.source
    if not source:
        typer.secho("no --source and no default source in config", fg="red", err=True)
        raise typer.Exit(1)
    contributor = owner or source

    r2 = None
    if not dry_run:
        from .storage import R2  # imported lazily so validate/dry-run need no creds
        r2 = R2(cfg)

    up = skip = flag = 0
    for d, errors, warnings, meta in _iter(path, source):
        if errors:
            skip += 1
            typer.secho(f"✗ {d.name}: {'; '.join(errors)} — skipped", fg="red")
            continue
        if dialect:
            meta["dialect"] = dialect
        meta["owner"] = owner or meta.get("owner", "")
        meta["contributor"] = contributor
        meta["dedup"] = project_hashes(d, meta)
        (d / META_NAME).write_text(json.dumps(meta, indent=2, ensure_ascii=False))

        if warnings:
            flag += 1
            typer.secho(f"⚠ {d.name}: {'; '.join(warnings)}", fg="yellow")
        if dry_run:
            up += 1
            typer.echo(f"  (dry-run) {meta['id']} ready — {len(meta['dedup'])} fingerprints")
            continue
        result = r2.upload_tree(d, f"{source}/{d.name}")
        up += 1
        typer.secho(f"↑ {meta['id']}  ({result.files} files, {result.bytes/1e6:.1f} MB)", fg="green")

    typer.echo(f"\n{'validated' if dry_run else 'uploaded'}: {up} · flagged: {flag} · skipped: {skip}")


if __name__ == "__main__":
    app()
