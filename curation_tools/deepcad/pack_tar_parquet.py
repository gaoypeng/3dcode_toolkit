"""
pack_tar_parquet.py
Pack the canonical directory tree into the 3DCodeVerse tar-shard + parquet layout,
1:1 matching the reference ilabai/3dcodeverse/shadertoy/3X:

  deepcad/<subfolder>/
      <subfolder>-00000.tar   # samples concatenated; each sample's files are a
      <subfolder>-00001.tar   #   contiguous, independently-openable sub-tar
      ...
      metadata.parquet        # one row/sample: text inline + media locator

Each sample's files are written in order under "<key>/...":
  captions.json (empty -> maintainer fills), code.py, meta.json,
  renders/{view_00..03.png, object.glb, model.step}, curation.json

parquet columns (mirrors 3X; shader_json -> curation_json):
  id, key, name, captions{detailed,instruction,factory},
  meta_json, curation_json, code, shard, byte_start, byte_len, n_files
"""
import io
import os
import json
import tarfile
import argparse
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


def add_bytes(tar, arcname, data):
    ti = tarfile.TarInfo(arcname)
    ti.size = len(data)
    tar.addfile(ti, io.BytesIO(data))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, help=".../corpus_3dcv/deepcad (bucket/name/ tree)")
    ap.add_argument("--out", required=True, help="output dir for tars + parquet")
    ap.add_argument("--subfolder", default="v1")
    ap.add_argument("--shard_mb", type=int, default=300)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    corpus = Path(args.corpus)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    SHARD = args.shard_mb * 1024 * 1024
    sf = args.subfolder

    samples = []
    for bucket in sorted(corpus.iterdir()):
        if bucket.is_dir():
            for d in sorted(bucket.iterdir()):
                if d.is_dir():
                    samples.append(d)
    if args.limit:
        samples = samples[: args.limit]
    print(f"Packing {len(samples)} samples (shard={args.shard_mb}MB) -> {out}/{sf}-NNNNN.tar")

    EMPTY_CAP = json.dumps({"detailed": "", "instruction": "", "factory": ""}).encode()

    rows = []
    shard_idx = 0
    tar = tarfile.open(out / f"{sf}-{shard_idx:05d}.tar", "w")
    try:
        for d in samples:
            if tar.offset > 0 and tar.offset >= SHARD:
                tar.close()
                shard_idx += 1
                tar = tarfile.open(out / f"{sf}-{shard_idx:05d}.tar", "w")

            key = d.name
            start = tar.offset
            nfiles = 0

            # meta.json: rewrite id to source/subfolder/key (3X convention)
            meta = json.loads((d / "meta.json").read_text())
            meta["id"] = f"deepcad/{sf}/{key}"
            meta_bytes = json.dumps(meta, ensure_ascii=False, indent=2).encode()
            code_bytes = (d / "code.py").read_bytes()
            cur_bytes = (d / "curation.json").read_bytes()

            # write in fixed order
            add_bytes(tar, f"{key}/captions.json", EMPTY_CAP); nfiles += 1
            add_bytes(tar, f"{key}/code.py", code_bytes); nfiles += 1
            add_bytes(tar, f"{key}/meta.json", meta_bytes); nfiles += 1
            rdir = d / "renders"
            for rname in ["view_00.png", "view_01.png", "view_02.png", "view_03.png",
                          "object.glb", "model.step"]:
                rp = rdir / rname
                if rp.exists():
                    tar.add(rp, arcname=f"{key}/renders/{rname}")
                    nfiles += 1
            add_bytes(tar, f"{key}/curation.json", cur_bytes); nfiles += 1

            byte_len = tar.offset - start
            rows.append({
                "id": f"deepcad/{sf}/{key}",
                "key": key,
                "name": meta.get("name", f"deepcad_{key}"),
                "captions": {"detailed": "", "instruction": "", "factory": ""},
                "meta_json": meta_bytes.decode(),
                "curation_json": cur_bytes.decode(),
                "code": code_bytes.decode("utf-8", "replace"),
                "shard": f"{sf}-{shard_idx:05d}.tar",
                "byte_start": start,
                "byte_len": byte_len,
                "n_files": nfiles,
            })
    finally:
        tar.close()

    schema = pa.schema([
        ("id", pa.string()), ("key", pa.string()), ("name", pa.string()),
        ("captions", pa.struct([("detailed", pa.string()),
                                ("instruction", pa.string()),
                                ("factory", pa.string())])),
        ("meta_json", pa.string()), ("curation_json", pa.string()),
        ("code", pa.string()), ("shard", pa.string()),
        ("byte_start", pa.int64()), ("byte_len", pa.int64()), ("n_files", pa.int32()),
    ])
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), out / "metadata.parquet")
    n_shards = shard_idx + 1
    print(f"Done: {len(rows)} rows, {n_shards} shards, metadata.parquet written.")


if __name__ == "__main__":
    main()
