#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

MAX_FRAME_COUNT = 50000
DEFAULT_SHARD_SIZE = 1000
SUPPORTED_PAYLOAD_LENGTHS = {200, 300}
SUPPORTED_PAYLOAD_POLICY_VERSION = 1
SCHEMA_VERSION = "common03.frame_pool_manifest.v2"
GENERATION_ALGORITHM = "splitmix64_payload_v2"
BIT_STORAGE_FORMAT = "packed_bits"
BIT_ORDER_WITHIN_BYTE = "lsb_first"
INTEGER_BYTE_ORDER = "not_applicable"
GENERATOR_VERSION = "common03.frame_pool.v2"
UINT64_MAX = (1 << 64) - 1


def splitmix64(value: int) -> int:
    value = (value + 0x9E3779B97F4A7C15) & UINT64_MAX
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & UINT64_MAX
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & UINT64_MAX
    return (value ^ (value >> 31)) & UINT64_MAX


def validate_payload_policy_version(payload_policy_version: int) -> None:
    if payload_policy_version != SUPPORTED_PAYLOAD_POLICY_VERSION:
        raise ValueError("unsupported payloadPolicyVersion")


def deterministic_payload_bit(
    master_seed: int,
    payload_length: int,
    frame_index: int,
    bit_index: int,
    payload_policy_version: int = SUPPORTED_PAYLOAD_POLICY_VERSION,
) -> int:
    validate_payload_policy_version(payload_policy_version)
    if not 0 <= master_seed <= UINT64_MAX:
        raise ValueError("master_seed must be in uint64 range")
    if payload_length <= 0:
        raise ValueError("payload_length must be positive")
    if frame_index < 0:
        raise IndexError("frame_index must be non-negative")
    if bit_index < 0 or bit_index >= payload_length:
        raise IndexError("bit_index outside payload_length")
    value = master_seed & UINT64_MAX
    value ^= (payload_policy_version * 0xA24BAED4963EE407) & UINT64_MAX
    value ^= (payload_length * 0xD1B54A32D192ED03) & UINT64_MAX
    value ^= (frame_index * 0xABC98388FB8FAC03) & UINT64_MAX
    value ^= (bit_index * 0x8CB92BA72F3D8DD7) & UINT64_MAX
    return splitmix64(value) & 1


def generate_payload_bits(
    master_seed: int,
    payload_length: int,
    frame_index: int,
    payload_policy_version: int = SUPPORTED_PAYLOAD_POLICY_VERSION,
) -> list[int]:
    return [
        deterministic_payload_bit(master_seed, payload_length, frame_index, bit_index, payload_policy_version)
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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def shard_file_name(start_frame: int, end_frame: int) -> str:
    return f"frames_{start_frame:06d}_{end_frame:06d}.bin"


def canonical_overall_hash_text(manifest: dict[str, Any]) -> str:
    lines = [
        f"schemaVersion={manifest['schemaVersion']}",
        f"framePoolId={manifest['framePoolId']}",
        f"payloadLength={manifest['payloadLength']}",
        f"totalFrames={manifest['totalFrames']}",
        f"shardSize={manifest['shardSize']}",
        f"masterSeed={manifest['masterSeed']}",
        f"payloadPolicyVersion={manifest['payloadPolicyVersion']}",
        f"generationAlgorithm={manifest['generationAlgorithm']}",
        f"bitStorageFormat={manifest['bitStorageFormat']}",
        f"bitOrderWithinByte={manifest['bitOrderWithinByte']}",
        f"bytesPerFrame={manifest['bytesPerFrame']}",
    ]
    for shard in manifest["shards"]:
        lines.extend(
            [
                f"shard.startFrame={shard['startFrame']}",
                f"shard.frameCount={shard['frameCount']}",
                f"shard.fileName={shard['fileName']}",
                f"shard.sizeBytes={shard['sizeBytes']}",
                f"shard.sha256={shard['sha256']}",
            ]
        )
    return "\n".join(lines) + "\n"


def compute_overall_hash(manifest: dict[str, Any]) -> str:
    return sha256_bytes(canonical_overall_hash_text(manifest).encode("utf-8"))


def validate_inputs(
    output_dir: Path,
    payload_length: int,
    frame_count: int,
    shard_size: int,
    master_seed: int,
    payload_policy_version: int,
    overwrite: bool,
) -> None:
    if not 0 <= master_seed <= UINT64_MAX:
        raise ValueError("masterSeed must be in uint64 range")
    if payload_length not in SUPPORTED_PAYLOAD_LENGTHS:
        raise ValueError("payloadLength must be 200 or 300")
    if frame_count <= 0 or frame_count > MAX_FRAME_COUNT:
        raise ValueError("frameCount must be in 1..50000")
    if shard_size <= 0:
        raise ValueError("shardSize must be positive")
    validate_payload_policy_version(payload_policy_version)


def write_pool(
    output_dir: Path,
    payload_length: int,
    frame_count: int,
    shard_size: int,
    master_seed: int,
    payload_policy_version: int = SUPPORTED_PAYLOAD_POLICY_VERSION,
    overwrite: bool = False,
) -> Path:
    validate_inputs(output_dir, payload_length, frame_count, shard_size, master_seed, payload_policy_version, overwrite)

    pool_dir = output_dir / f"k{payload_length}"
    if pool_dir.exists() and overwrite:
        shutil.rmtree(pool_dir)
    pool_dir.mkdir(parents=True, exist_ok=True)
    if any(pool_dir.iterdir()) and not overwrite:
        raise FileExistsError(f"pool directory already contains files: {pool_dir}")

    bytes_per_frame = packed_payload_byte_count(payload_length)
    shards: list[dict[str, object]] = []

    for start_frame in range(0, frame_count, shard_size):
        count = min(shard_size, frame_count - start_frame)
        end_frame = start_frame + count - 1
        file_name = shard_file_name(start_frame, end_frame)
        shard_path = pool_dir / file_name
        with shard_path.open("wb") as handle:
            for frame_index in range(start_frame, start_frame + count):
                bits = generate_payload_bits(master_seed, payload_length, frame_index, payload_policy_version)
                packed = pack_bits(bits)
                if len(packed) != bytes_per_frame:
                    raise RuntimeError("internal packed byte count mismatch")
                handle.write(packed)
        shards.append(
            {
                "startFrame": start_frame,
                "frameCount": count,
                "fileName": file_name,
                "sizeBytes": shard_path.stat().st_size,
                "sha256": sha256_file(shard_path),
            }
        )

    manifest: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "framePoolId": f"payload_k{payload_length}_seed{master_seed}_policy{payload_policy_version}_frames{frame_count}",
        "payloadLength": payload_length,
        "totalFrames": frame_count,
        "shardSize": shard_size,
        "masterSeed": master_seed,
        "payloadSeed": master_seed,
        "payloadPolicyVersion": payload_policy_version,
        "generationAlgorithm": GENERATION_ALGORITHM,
        "bitStorageFormat": BIT_STORAGE_FORMAT,
        "bitOrderWithinByte": BIT_ORDER_WITHIN_BYTE,
        "integerByteOrder": INTEGER_BYTE_ORDER,
        "generatorVersion": GENERATOR_VERSION,
        "bytesPerFrame": bytes_per_frame,
        "shards": shards,
    }
    manifest["overallHash"] = compute_overall_hash(manifest)
    manifest_path = pool_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Common-03 deterministic payload frame pools.")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--master-seed", type=int, default=2026072001)
    parser.add_argument("--frame-count", type=int, default=24)
    parser.add_argument("--shard-size", type=int, default=DEFAULT_SHARD_SIZE)
    parser.add_argument("--payload-length", type=int, nargs="+", default=[200, 300])
    parser.add_argument("--payload-policy-version", type=int, default=SUPPORTED_PAYLOAD_POLICY_VERSION)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    validate_inputs(
        args.output_dir,
        args.payload_length[0] if args.payload_length else 0,
        args.frame_count,
        args.shard_size,
        args.master_seed,
        args.payload_policy_version,
        args.overwrite,
    )
    if args.output_dir.exists() and any(args.output_dir.iterdir()) and args.overwrite:
        shutil.rmtree(args.output_dir)
    elif args.output_dir.exists() and any(args.output_dir.iterdir()) and not args.overwrite:
        raise FileExistsError("output directory is not empty; use --overwrite")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    manifests = [
        write_pool(
            args.output_dir,
            payload_length,
            args.frame_count,
            args.shard_size,
            args.master_seed,
            args.payload_policy_version,
            overwrite=args.overwrite,
        )
        for payload_length in args.payload_length
    ]
    for manifest in manifests:
        print(f"COMMON-03 FRAME POOL: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
