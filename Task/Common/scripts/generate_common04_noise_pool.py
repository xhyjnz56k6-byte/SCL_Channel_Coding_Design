#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

MASK = (1 << 64) - 1
MAGIC = b"SCLN04"
HEADER_VERSION = 1
SCHEMA = "common04.noise_pool_manifest.v1"
DOMAIN = 0x4E4F4953455F3034
POLICY = 1


def splitmix64(value: int) -> int:
    value = (value + 0x9E3779B97F4A7C15) & MASK
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK
    return (value ^ (value >> 31)) & MASK


def word(seed: int, group: int, frame: int, symbol: int) -> int:
    value = DOMAIN
    value ^= (seed * 0xD6E8FEB86659FD93) & MASK
    value ^= (group * 0xA0761D6478BD642F) & MASK
    value ^= (frame * 0xE7037ED1A0B428DB) & MASK
    value ^= (symbol * 0x8EBC6AF09C88C6E3) & MASK
    value ^= (POLICY * 0x589965CC75374CC3) & MASK
    return splitmix64(value)


def uniform_open(value: int) -> float:
    return ((value >> 11) + 1) / 9007199254740994.0


def gaussian(seed: int, group: int, frame: int, symbol: int) -> float:
    u1 = uniform_open(word(seed, group, frame, symbol * 2))
    u2 = uniform_open(word(seed, group, frame, symbol * 2 + 1))
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def canonical(manifest: dict) -> str:
    lines = [
        f"schemaVersion={manifest['schemaVersion']}",
        f"masterNoiseSeed={manifest['masterNoiseSeed']}",
        f"noiseGroupId={manifest['noiseGroupId']}",
        f"noisePolicyVersion={manifest['noisePolicyVersion']}",
        f"totalFrames={manifest['totalFrames']}",
        f"symbolsPerFrame={manifest['symbolsPerFrame']}",
        f"framesPerShard={manifest['framesPerShard']}",
        f"samplePrecision={manifest['samplePrecision']}",
        f"sampleByteOrder={manifest['sampleByteOrder']}",
        f"generationAlgorithm={manifest['generationAlgorithm']}",
    ]
    for shard in manifest["shards"]:
        lines.extend([
            f"shard.fileName={shard['fileName']}",
            f"shard.firstFrameIndex={shard['firstFrameIndex']}",
            f"shard.frameCount={shard['frameCount']}",
            f"shard.sizeBytes={shard['sizeBytes']}",
            f"shard.sha256={shard['sha256']}",
        ])
    return "\n".join(lines) + "\n"


def write_shard(path: Path, seed: int, group: int, first: int, count: int, symbols: int) -> None:
    with path.open("wb") as handle:
        handle.write(MAGIC)
        handle.write(struct.pack("<IQQQQQQ", HEADER_VERSION, first, count, symbols, seed, group, POLICY))
        for frame in range(first, first + count):
            for symbol in range(symbols):
                handle.write(struct.pack("<d", gaussian(seed, group, frame, symbol)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--master-noise-seed", type=int, default=2026072101)
    parser.add_argument("--noise-group-id", type=int, default=0)
    parser.add_argument("--frame-count", type=int, default=100)
    parser.add_argument("--symbols-per-frame", type=int, default=32)
    parser.add_argument("--frames-per-shard", type=int, default=25)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    output = Path(args.output_dir)
    if output.exists() and any(output.iterdir()) and not args.overwrite:
        raise SystemExit("refuse overwrite without --overwrite")
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schemaVersion": SCHEMA,
        "noisePoolId": "",
        "masterNoiseSeed": args.master_noise_seed,
        "noiseGroupId": args.noise_group_id,
        "noisePolicyVersion": POLICY,
        "totalFrames": args.frame_count,
        "symbolsPerFrame": args.symbols_per_frame,
        "framesPerShard": args.frames_per_shard,
        "samplePrecision": "float64",
        "sampleByteOrder": "little_endian",
        "generationAlgorithm": "splitmix64_box_muller_v1",
        "shards": [],
        "overallHash": "",
    }
    for first in range(0, args.frame_count, args.frames_per_shard):
        count = min(args.frames_per_shard, args.frame_count - first)
        name = f"noise_{first:06d}_{first + count - 1:06d}.bin"
        path = output / name
        write_shard(path, args.master_noise_seed, args.noise_group_id, first, count, args.symbols_per_frame)
        manifest["shards"].append({
            "fileName": name,
            "firstFrameIndex": first,
            "frameCount": count,
            "sizeBytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    manifest["overallHash"] = hashlib.sha256(canonical(manifest).encode("utf-8")).hexdigest()
    manifest["noisePoolId"] = manifest["overallHash"][:16]
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(output / "manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
