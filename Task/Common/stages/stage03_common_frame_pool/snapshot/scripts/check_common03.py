#!/usr/bin/env python3
from __future__ import annotations

import filecmp
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from generate_common03_frame_pool import (
    BIT_STORAGE_FORMAT,
    ENDIANNESS,
    GENERATION_ALGORITHM,
    generate_payload_bits,
    packed_payload_byte_count,
    unpack_bits,
)

ALLOWED_PREFIXES = (
    "Task/Common/",
)


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_failure(failures: list[str], message: str) -> None:
    failures.append(message)


def check_git_scope(root: Path, failures: list[str]) -> None:
    diff = run(["git", "diff", "--name-only", "main...HEAD"], root)
    if diff.returncode != 0:
        add_failure(failures, diff.stderr.strip())
        return
    for raw in diff.stdout.splitlines():
        path = raw.strip().replace("\\", "/")
        if not path:
            continue
        if path.startswith("Task/Common/Plan/"):
            add_failure(failures, "Task/Common/Plan must not be committed")
        if path.startswith("Task/Common/build/"):
            add_failure(failures, "Task/Common/build must not be committed")
        if path.startswith(("Task/BCH/", "Task/CC/", "Task/LDPC/")):
            add_failure(failures, f"out-of-scope path in committed diff: {path}")
        if not any(path.startswith(prefix) for prefix in ALLOWED_PREFIXES):
            add_failure(failures, f"path not allowed for Common-03 branch diff: {path}")


def check_no_later_stage_markers(root: Path, failures: list[str]) -> None:
    files = []
    for folder in [
        root / "Task/Common/include/common",
        root / "Task/Common/tests/stage03",
    ]:
        if folder.exists():
            files.extend(path for path in folder.rglob("*") if path.is_file())
    files.extend(
        path
        for path in [
            root / "Task/Common/scripts/generate_common03_frame_pool.py",
            root / "Task/Common/scripts/build_common03.py",
        ]
        if path.is_file()
    )
    joined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in files)
    forbidden = [
        "std::normal_distribution",
        "normal_distribution<",
        "awgnTransmit",
        "bpskModulate",
        "computeSigma",
        "llrValues[i]",
        "bitErrors /",
        "frameErrors /",
        "StopController",
        "resumeCheckpoint",
        "writeCheckpoint",
    ]
    for marker in forbidden:
        if marker in joined:
            add_failure(failures, f"later-stage implementation marker found: {marker}")


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_frame_from_manifest(manifest_path: Path, frame_index: int) -> list[int]:
    manifest = load_manifest(manifest_path)
    if frame_index < 0 or frame_index >= manifest["totalFrames"]:
        raise IndexError("frameIndex outside frame pool")
    bytes_per_frame = manifest["bytesPerFrame"]
    for shard in manifest["shards"]:
        start = shard["startFrame"]
        count = shard["frameCount"]
        if start <= frame_index < start + count:
            offset = (frame_index - start) * bytes_per_frame
            with (manifest_path.parent / shard["fileName"]).open("rb") as handle:
                handle.seek(offset)
                data = handle.read(bytes_per_frame)
            return unpack_bits(data, manifest["payloadLength"])
    raise RuntimeError("frameIndex not covered by any shard")


def check_manifest_and_payload(manifest_path: Path, expected_seed: int, failures: list[str]) -> None:
    manifest = load_manifest(manifest_path)
    payload_length = manifest.get("payloadLength")
    if payload_length not in (200, 300):
        add_failure(failures, f"invalid payloadLength in {manifest_path}")
    if manifest.get("totalFrames", 0) <= 0 or manifest.get("totalFrames", 0) > 50000:
        add_failure(failures, f"invalid totalFrames in {manifest_path}")
    if manifest.get("shardSize", 0) <= 0:
        add_failure(failures, f"invalid shardSize in {manifest_path}")
    if manifest.get("masterSeed") != expected_seed or manifest.get("payloadSeed") != expected_seed:
        add_failure(failures, f"seed mismatch in {manifest_path}")
    if manifest.get("generationAlgorithm") != GENERATION_ALGORITHM:
        add_failure(failures, f"generationAlgorithm mismatch in {manifest_path}")
    if manifest.get("bitStorageFormat") != BIT_STORAGE_FORMAT:
        add_failure(failures, f"bitStorageFormat mismatch in {manifest_path}")
    if manifest.get("endianness") != ENDIANNESS:
        add_failure(failures, f"endianness mismatch in {manifest_path}")
    if manifest.get("bytesPerFrame") != packed_payload_byte_count(payload_length):
        add_failure(failures, f"bytesPerFrame mismatch in {manifest_path}")

    total_shard_frames = 0
    for shard in manifest.get("shards", []):
        shard_path = manifest_path.parent / shard["fileName"]
        if not shard_path.exists():
            add_failure(failures, f"missing shard file: {shard_path}")
            continue
        if sha256_file(shard_path) != shard["sha256"]:
            add_failure(failures, f"shard SHA256 mismatch: {shard_path}")
        expected_size = shard["frameCount"] * manifest["bytesPerFrame"]
        if shard_path.stat().st_size != expected_size:
            add_failure(failures, f"shard byte size mismatch: {shard_path}")
        total_shard_frames += shard["frameCount"]
    if total_shard_frames != manifest.get("totalFrames"):
        add_failure(failures, f"shard frame counts do not sum to totalFrames in {manifest_path}")

    indices = sorted({0, manifest["totalFrames"] // 2, manifest["totalFrames"] - 1})
    for index in indices:
        actual = read_frame_from_manifest(manifest_path, index)
        expected = generate_payload_bits(expected_seed, payload_length, index)
        if actual != expected:
            add_failure(failures, f"payload mismatch at frame {index} in {manifest_path}")
    try:
        read_frame_from_manifest(manifest_path, manifest["totalFrames"])
        add_failure(failures, f"out-of-range read did not fail in {manifest_path}")
    except IndexError:
        pass


def check_generation(root: Path, failures: list[str]) -> list[Path]:
    build_dir = root / "Task/Common/build/stage03"
    pool_a = build_dir / "pool_a"
    pool_b = build_dir / "pool_b"
    pool_c = build_dir / "pool_c"
    for directory in [pool_a, pool_b, pool_c]:
        if directory.exists():
            shutil.rmtree(directory)

    seed = 2026072001
    for directory, current_seed in [(pool_a, seed), (pool_b, seed), (pool_c, seed + 1)]:
        completed = run(
            [
                sys.executable,
                "Task/Common/scripts/generate_common03_frame_pool.py",
                "--output-dir",
                str(directory),
                "--master-seed",
                str(current_seed),
                "--frame-count",
                "24",
                "--shard-size",
                "10",
                "--payload-length",
                "200",
                "300",
            ],
            root,
        )
        if completed.returncode != 0:
            add_failure(failures, completed.stderr.strip() or completed.stdout.strip())

    manifests = [pool_a / "k200/manifest.json", pool_a / "k300/manifest.json"]
    for manifest in manifests:
        check_manifest_and_payload(manifest, seed, failures)

    for relative in [
        Path("k200/frames_000000_000009.bin"),
        Path("k200/frames_000010_000019.bin"),
        Path("k200/frames_000020_000023.bin"),
        Path("k300/frames_000000_000009.bin"),
    ]:
        if not filecmp.cmp(pool_a / relative, pool_b / relative, shallow=False):
            add_failure(failures, f"same seed regeneration mismatch: {relative}")
    if filecmp.cmp(pool_a / "k200/frames_000000_000009.bin", pool_c / "k200/frames_000000_000009.bin", shallow=False):
        add_failure(failures, "different seed should alter at least one K=200 shard")

    return manifests


def check_cpp(root: Path, manifests: list[Path], failures: list[str]) -> None:
    build = run([sys.executable, "Task/Common/scripts/build_common03.py"], root)
    if build.returncode != 0:
        add_failure(failures, build.stdout + build.stderr)
        return
    executable = root / "Task/Common/build/stage03/test_common03_frame_pool.exe"
    command = [str(executable), *(str(manifest) for manifest in manifests)]
    completed = run(command, root)
    if completed.returncode != 0:
        add_failure(failures, completed.stdout + completed.stderr)


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    failures: list[str] = []
    manifests = check_generation(root, failures)
    check_cpp(root, manifests, failures)
    check_no_later_stage_markers(root, failures)
    check_git_scope(root, failures)

    if failures:
        print("COMMON-03 CHECK: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("COMMON-03 CHECK: PASS")
    print("Gate: PASS_COMMON_FRAME_POOL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
