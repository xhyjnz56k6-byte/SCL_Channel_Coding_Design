#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from generate_common04_noise_pool import MAGIC, HEADER_VERSION, SCHEMA, canonical


def validate(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data["schemaVersion"] != SCHEMA:
        raise ValueError("bad schemaVersion")
    expected = 0
    for shard in data["shards"]:
        if shard["firstFrameIndex"] != expected:
            raise ValueError("shard gap or overlap")
        shard_path = path.parent / shard["fileName"]
        raw = shard_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != shard["sha256"]:
            raise ValueError("shard sha256 mismatch")
        if len(raw) != shard["sizeBytes"]:
            raise ValueError("shard size mismatch")
        magic = raw[:6]
        header = struct.unpack("<IQQQQQQ", raw[6:58])
        if magic != MAGIC or header[0] != HEADER_VERSION:
            raise ValueError("bad shard header")
        if header[1] != shard["firstFrameIndex"] or header[2] != shard["frameCount"] or header[3] != data["symbolsPerFrame"]:
            raise ValueError("header/manifest mismatch")
        expected += shard["frameCount"]
    if expected != data["totalFrames"]:
        raise ValueError("frame count mismatch")
    if hashlib.sha256(canonical(data).encode("utf-8")).hexdigest() != data["overallHash"]:
        raise ValueError("overallHash mismatch")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    args = parser.parse_args()
    validate(Path(args.manifest))
    print("COMMON-04 NOISE POOL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
