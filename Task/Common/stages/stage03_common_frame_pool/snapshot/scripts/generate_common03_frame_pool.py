#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

MAX_FRAME_COUNT = 50000
GENERATION_ALGORITHM = "splitmix64_payload_v1"
BIT_STORAGE_FORMAT = "packed_bits_lsb_first"
ENDIANNESS = "little"
GENERATOR_VERSION = "common03.frame_pool.v1"


def splitmix64(value: int) -> int:
    value = (value + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    return (value ^ (value >> 31)) & 0xFFFFFFFFFFFFFFFF


def deterministic_payload_bit(master_seed: int, payload_length: int, frame_index: int, bit_index: int) -> int:
    if payload_length <= 0:
        raise ValueError("payload_length must be positive")
    if bit_index >= payload_length:
        raise IndexError("bit_index outside payload_length")
    value = master_seed & 0xFFFFFFFFFFFFFFFF
    value ^= (payload_length * 0xD1B54A32D192ED03) & 0xFFFFFFFFFFFFFFFF
    value ^= (frame_index * 0xABC98388FB8FAC03) & 0xFFFFFFFFFFFFFFFF
    value ^= (bit_index * 0x8CB92BA72F3D8DD7) & 0xFFFFFFFFFFFFFFFF
    return splitmix64(value) & 1


def generate_payload_bits(master_seed: int, payload_length: int, frame_index: int) -> list[int]:
    return [
        deterministic_payload_bit(master_seed, payload_length, frame_index, bit_index)
        for bit_index in range(payload_length)
    ]


def packed_payload_byte_count(payload_length: int) -> int:
    if payload_length <= 0:
        raise ValueError("payload_length must be positive")
    return (payload_length + 7) // 8


def pack_bits(bits: list[int]) -> bytes:
    packed = bytearray(packed_payload_byte_count(len(bits)))
    for bit_index, bit in enumerate(bits):
        if bit not in (0, 1):
            raise ValueError("payloadBits contains a non-binary bit")
        if bit:
            packed[bit_index // 8] |= 1 << (bit_index % 8)
    return bytes(packed)


def unpack_bits(data: bytes, payload_length: int) -> list[int]:
    if len(data) != packed_payload_byte_count(payload_length):
        raise ValueError("packed payload byte count mismatch")
    return [(data[bit_index // 8] >> (bit_index % 8)) & 1 for bit_index in range(payload_length)]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def shard_file_name(start_frame: int, end_frame: int) -> str:
    return f"frames_{start_frame:06d}_{end_frame:06d}.bin"


def write_pool(output_dir: Path, payload_length: int, frame_count: int, shard_size: int, master_seed: int) -> Path:
    if payload_length not in (200, 300):
        raise ValueError("payload_length must be 200 or 300")
    if frame_count <= 0 or frame_count > MAX_FRAME_COUNT:
        raise ValueError("frame_count must be in 1..50000")
    if shard_size <= 0:
        raise ValueError("shard_size must be positive")

    pool_dir = output_dir / f"k{payload_length}"
    pool_dir.mkdir(parents=True, exist_ok=True)
    bytes_per_frame = packed_payload_byte_count(payload_length)
    shards: list[dict[str, object]] = []

    for start_frame in range(0, frame_count, shard_size):
        count = min(shard_size, frame_count - start_frame)
        end_frame = start_frame + count - 1
        file_name = shard_file_name(start_frame, end_frame)
        shard_path = pool_dir / file_name
        with shard_path.open("wb") as handle:
            for frame_index in range(start_frame, start_frame + count):
                bits = generate_payload_bits(master_seed, payload_length, frame_index)
                packed = pack_bits(bits)
                if len(packed) != bytes_per_frame:
                    raise RuntimeError("internal packed byte count mismatch")
                handle.write(packed)
        shards.append(
            {
                "startFrame": start_frame,
                "frameCount": count,
                "fileName": file_name,
                "sha256": sha256_file(shard_path),
            }
        )

    manifest = {
        "schemaVersion": "common03.frame_pool_manifest.v1",
        "framePoolId": f"payload_k{payload_length}_seed{master_seed}_frames{frame_count}",
        "payloadLength": payload_length,
        "totalFrames": frame_count,
        "shardSize": shard_size,
        "masterSeed": master_seed,
        "payloadSeed": master_seed,
        "generationAlgorithm": GENERATION_ALGORITHM,
        "bitStorageFormat": BIT_STORAGE_FORMAT,
        "endianness": ENDIANNESS,
        "createdTime": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "generatorVersion": GENERATOR_VERSION,
        "bytesPerFrame": bytes_per_frame,
        "shards": shards,
    }
    manifest_path = pool_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Common-03 deterministic payload frame pools.")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--master-seed", type=int, default=2026072001)
    parser.add_argument("--frame-count", type=int, default=24)
    parser.add_argument("--shard-size", type=int, default=10)
    parser.add_argument("--payload-length", type=int, nargs="+", default=[200, 300])
    args = parser.parse_args()

    manifests = [
        write_pool(args.output_dir, payload_length, args.frame_count, args.shard_size, args.master_seed)
        for payload_length in args.payload_length
    ]
    for manifest in manifests:
        print(f"COMMON-03 FRAME POOL: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
