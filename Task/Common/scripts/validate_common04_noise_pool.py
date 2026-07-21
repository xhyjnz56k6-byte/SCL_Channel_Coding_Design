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
    if not data.get("noisePoolId") or data.get("samplePrecision") != "float64" or data.get("sampleByteOrder") != "little_endian" or data.get("generationAlgorithm") != "splitmix64_box_muller_v1":
        raise ValueError("unsupported noise pool identity or sample format")
    expected = 0
    names: set[str] = set()
    header_bytes = 58
    for index, shard in enumerate(data["shards"]):
        if shard["firstFrameIndex"] != expected:
            raise ValueError("shard gap or overlap")
        if shard["fileName"] in names:
            raise ValueError("duplicate shard file name")
        names.add(shard["fileName"])
        if len(shard["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in shard["sha256"]):
            raise ValueError("bad shard sha256 format")
        if index + 1 < len(data["shards"]) and shard["frameCount"] != data["framesPerShard"]:
            raise ValueError("non-final shard count mismatch")
        expected_size = header_bytes + shard["frameCount"] * data["symbolsPerFrame"] * 8
        if shard["sizeBytes"] != expected_size:
            raise ValueError("shard size formula mismatch")
        shard_path = path.parent / shard["fileName"]
        if not shard_path.exists():
            raise ValueError("missing shard file")
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
    if len(data["overallHash"]) != 64 or any(c not in "0123456789abcdef" for c in data["overallHash"]):
        raise ValueError("bad overallHash format")
    if hashlib.sha256(canonical(data).encode("utf-8")).hexdigest() != data["overallHash"]:
        raise ValueError("overallHash mismatch")
    if data["noisePoolId"] != data["overallHash"][:16]:
        raise ValueError("noisePoolId mismatch")
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
