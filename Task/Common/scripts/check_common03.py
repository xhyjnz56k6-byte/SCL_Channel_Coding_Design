#!/usr/bin/env python3
from __future__ import annotations

import csv
import filecmp
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from generate_common03_frame_pool import (
    BIT_ORDER_WITHIN_BYTE,
    BIT_STORAGE_FORMAT,
    GENERATION_ALGORITHM,
    INTEGER_BYTE_ORDER,
    SCHEMA_VERSION,
    SUPPORTED_PAYLOAD_POLICY_VERSION,
    canonical_overall_hash_text,
    compute_overall_hash,
    generate_payload_bits,
    packed_payload_byte_count,
    pack_bits,
    unpack_bits,
)

ALLOWED_PREFIXES = ("Task/Common/",)
STAGE_DIR = Path("Task/Common/stages/stage03_common_frame_pool")
ORIGINAL_BASE = "fe6cfa0164afd097adb972a51afd73240105c188"
ORIGINAL_CONTENT = "6c304d0ef10fb7620c05ee1ef54b5d4a58f3fe00"
ORIGINAL_FUNCTIONAL_FILES = [
    "Task/Common/include/common/frame_pool.hpp",
    "Task/Common/scripts/build_common03.py",
    "Task/Common/scripts/check_common03.py",
    "Task/Common/scripts/generate_common03_frame_pool.py",
    "Task/Common/tests/stage03/test_common03_frame_pool.cpp",
]
GOLDEN = {
    (2026072001, 200, 0): "1110101101010011100010111010110001010011111111100111000101000100",
    (2026072001, 200, 999): "1001101010011010100000111010011100011111101001111000100011011110",
    (2026072001, 300, 0): "0011100101011101010000100100101010100011110011100010101101101110",
    (2026072001, 300, 1000): "0101001010010011011011011001100111101001000000101110101100101101",
}


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


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def recompute_overall(manifest: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_overall_hash_text(manifest).encode("utf-8")).hexdigest()


def validate_manifest(manifest_path: Path, verify_files: bool = True) -> None:
    manifest = load_manifest(manifest_path)
    required = [
        "schemaVersion", "framePoolId", "payloadLength", "totalFrames", "shardSize", "masterSeed",
        "payloadPolicyVersion", "generationAlgorithm", "bitStorageFormat", "bitOrderWithinByte",
        "integerByteOrder", "bytesPerFrame", "overallHash", "shards",
    ]
    for key in required:
        if key not in manifest:
            raise ValueError(f"missing {key}")
    if manifest["schemaVersion"] != SCHEMA_VERSION:
        raise ValueError("unsupported schemaVersion")
    if not manifest["framePoolId"]:
        raise ValueError("framePoolId must not be empty")
    if manifest["payloadLength"] not in (200, 300):
        raise ValueError("payloadLength must be 200 or 300")
    if not 1 <= manifest["totalFrames"] <= 50000:
        raise ValueError("totalFrames outside supported range")
    if manifest["shardSize"] <= 0:
        raise ValueError("shardSize must be positive")
    if manifest["bytesPerFrame"] != packed_payload_byte_count(manifest["payloadLength"]):
        raise ValueError("bytesPerFrame mismatch")
    if manifest["payloadPolicyVersion"] != SUPPORTED_PAYLOAD_POLICY_VERSION:
        raise ValueError("unsupported payloadPolicyVersion")
    if manifest["generationAlgorithm"] != GENERATION_ALGORITHM:
        raise ValueError("unsupported generationAlgorithm")
    if manifest["bitStorageFormat"] != BIT_STORAGE_FORMAT:
        raise ValueError("unsupported bitStorageFormat")
    if manifest["bitOrderWithinByte"] != BIT_ORDER_WITHIN_BYTE:
        raise ValueError("unsupported bitOrderWithinByte")
    if manifest["integerByteOrder"] != INTEGER_BYTE_ORDER:
        raise ValueError("unsupported integerByteOrder")
    if not isinstance(manifest["shards"], list) or not manifest["shards"]:
        raise ValueError("manifest must contain shards")
    if not is_lower_sha(manifest["overallHash"]):
        raise ValueError("overallHash format invalid")

    expected_start = 0
    total = 0
    names: set[str] = set()
    for index, shard in enumerate(manifest["shards"]):
        for key in ["startFrame", "frameCount", "fileName", "sizeBytes", "sha256"]:
            if key not in shard:
                raise ValueError(f"missing shard {key}")
        if shard["startFrame"] != expected_start:
            raise ValueError("shards must be contiguous without gaps or overlap")
        if shard["frameCount"] <= 0:
            raise ValueError("shard frameCount must be positive")
        if index + 1 < len(manifest["shards"]) and shard["frameCount"] != manifest["shardSize"]:
            raise ValueError("non-final shard frameCount must equal shardSize")
        if index + 1 == len(manifest["shards"]) and shard["frameCount"] > manifest["shardSize"]:
            raise ValueError("final shard frameCount must not exceed shardSize")
        if not shard["fileName"] or ".." in shard["fileName"] or "/" in shard["fileName"] or "\\" in shard["fileName"] or ":" in shard["fileName"]:
            raise ValueError("unsafe shard fileName")
        if shard["fileName"] in names:
            raise ValueError("duplicate shard fileName")
        names.add(shard["fileName"])
        if not is_lower_sha(shard["sha256"]):
            raise ValueError("shard sha256 format invalid")
        expected_size = shard["frameCount"] * manifest["bytesPerFrame"]
        if shard["sizeBytes"] != expected_size:
            raise ValueError("shard sizeBytes mismatch")
        if verify_files:
            shard_path = manifest_path.parent / shard["fileName"]
            if not shard_path.exists():
                raise ValueError("missing shard file")
            if shard_path.stat().st_size != shard["sizeBytes"]:
                raise ValueError("shard file size mismatch")
            if sha256_file(shard_path) != shard["sha256"]:
                raise ValueError("shard SHA256 mismatch")
        expected_start += shard["frameCount"]
        total += shard["frameCount"]
    if total != manifest["totalFrames"] or expected_start != manifest["totalFrames"]:
        raise ValueError("shard frame counts must sum to totalFrames")
    if recompute_overall(manifest) != manifest["overallHash"]:
        raise ValueError("overallHash mismatch")


def is_lower_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


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
            if len(data) != bytes_per_frame:
                raise ValueError("short read from shard")
            return unpack_bits(data, manifest["payloadLength"])
    raise RuntimeError("frameIndex not covered by any shard")


def generate_fixture(root: Path, output_dir: Path, seed: int = 2026072001, overwrite: bool = True) -> list[Path]:
    cmd = [
        sys.executable, "Task/Common/scripts/generate_common03_frame_pool.py",
        "--output-dir", str(output_dir), "--master-seed", str(seed), "--frame-count", "24",
        "--shard-size", "10", "--payload-length", "200", "300", "--payload-policy-version", "1",
    ]
    if overwrite:
        cmd.append("--overwrite")
    completed = run(cmd, root)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    return [output_dir / "k200/manifest.json", output_dir / "k300/manifest.json"]


def check_generation(root: Path, failures: list[str]) -> list[Path]:
    build_dir = root / "Task/Common/build/stage03"
    pool_a = build_dir / "pool_a"
    pool_b = build_dir / "pool_b"
    pool_c = build_dir / "pool_c"
    manifests = generate_fixture(root, pool_a, overwrite=True)
    generate_fixture(root, pool_b, overwrite=True)
    generate_fixture(root, pool_c, seed=2026072002, overwrite=True)

    for manifest in manifests:
        try:
            validate_manifest(manifest)
        except Exception as exc:
            add_failure(failures, f"manifest validation failed {manifest}: {exc}")

    for relative in [Path("k200/manifest.json"), Path("k300/manifest.json")]:
        if not filecmp.cmp(pool_a / relative, pool_b / relative, shallow=False):
            add_failure(failures, f"same seed manifest mismatch: {relative}")
    for relative in [Path("k200/frames_000000_000009.bin"), Path("k300/frames_000000_000009.bin")]:
        if not filecmp.cmp(pool_a / relative, pool_b / relative, shallow=False):
            add_failure(failures, f"same seed shard mismatch: {relative}")
    if filecmp.cmp(pool_a / "k200/frames_000000_000009.bin", pool_c / "k200/frames_000000_000009.bin", shallow=False):
        add_failure(failures, "different seed should alter at least one K=200 shard")

    for manifest in manifests:
        data = load_manifest(manifest)
        for index in sorted({0, data["shardSize"] - 1, data["shardSize"], data["totalFrames"] // 2, data["totalFrames"] - 1}):
            actual = read_frame_from_manifest(manifest, index)
            expected = generate_payload_bits(data["masterSeed"], data["payloadLength"], index, data["payloadPolicyVersion"])
            if actual != expected:
                add_failure(failures, f"payload mismatch at frame {index} in {manifest}")
        try:
            read_frame_from_manifest(manifest, -1)
            add_failure(failures, "negative frameIndex did not fail")
        except IndexError:
            pass
        try:
            read_frame_from_manifest(manifest, data["totalFrames"])
            add_failure(failures, "frameIndex==totalFrames did not fail")
        except IndexError:
            pass

    repeat = run([
        sys.executable, "Task/Common/scripts/generate_common03_frame_pool.py", "--output-dir", str(pool_a),
        "--master-seed", "2026072001", "--frame-count", "24", "--shard-size", "10", "--payload-length", "200",
    ], root)
    if repeat.returncode == 0:
        add_failure(failures, "generator should refuse overwrite without --overwrite")
    return manifests


def check_golden_vectors(failures: list[str]) -> None:
    for key, expected in GOLDEN.items():
        actual = "".join(str(bit) for bit in generate_payload_bits(*key)[:64])
        if actual != expected:
            add_failure(failures, f"golden vector mismatch: {key}")
    known = [0, 1, 1, 0, 1, 0, 0, 1, 1]
    if pack_bits(known).hex() != "9601":
        add_failure(failures, "explicit packed byte fixture mismatch")
    for payload_length in [200, 300]:
        packed = pack_bits(generate_payload_bits(2026072001, payload_length, 0))
        if packed[-1] & 0xF0:
            add_failure(failures, f"unused tail bits are not zero for K={payload_length}")


def check_cpp(root: Path, manifests: list[Path], failures: list[str]) -> None:
    build = run([sys.executable, "Task/Common/scripts/build_common03.py"], root)
    if build.returncode != 0:
        add_failure(failures, build.stdout + build.stderr)
        return
    executable = root / "Task/Common/build/stage03/test_common03_frame_pool.exe"
    completed = run([str(executable), *(str(manifest) for manifest in manifests)], root)
    if completed.returncode != 0:
        add_failure(failures, completed.stdout + completed.stderr)


def mutate_manifest_copy(source_manifest: Path, name: str) -> Path:
    target = source_manifest.parent.parent / f"neg_{name}"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source_manifest.parent, target)
    return target / "manifest.json"


def set_overall(manifest: dict[str, Any]) -> None:
    manifest["overallHash"] = compute_overall_hash(manifest)


def run_negative_tests(root: Path, source_manifest: Path, failures: list[str]) -> None:
    rows: list[dict[str, str]] = []

    def record(name: str, mutation: str, expected: str, fn: Callable[[Path], None]) -> None:
        manifest_path = mutate_manifest_copy(source_manifest, name)
        try:
            fn(manifest_path)
            validate_manifest(manifest_path)
            actual = "NO_FAILURE"
            verdict = "FAIL"
        except Exception as exc:
            actual = str(exc)
            verdict = "PASS" if expected in actual else "FAIL"
        rows.append({"testName": name, "mutation": mutation, "expectedFailure": expected, "actualFailure": actual, "verdict": verdict})
        if verdict != "PASS":
            add_failure(failures, f"negative test failed: {name}; actual={actual}; expected={expected}")

    def edit_json(fn: Callable[[dict[str, Any]], None]) -> Callable[[Path], None]:
        def inner(path: Path) -> None:
            data = load_manifest(path)
            fn(data)
            write_manifest(path, data)
        return inner

    def edit_json_rehash(fn: Callable[[dict[str, Any]], None]) -> Callable[[Path], None]:
        def inner(path: Path) -> None:
            data = load_manifest(path)
            fn(data)
            set_overall(data)
            write_manifest(path, data)
        return inner

    record("delete_schemaVersion", "delete schemaVersion", "missing schemaVersion", edit_json(lambda d: d.pop("schemaVersion")))
    record("bad_schemaVersion", "unsupported schemaVersion", "unsupported schemaVersion", edit_json(lambda d: d.__setitem__("schemaVersion", "bad")))
    record("delete_payloadPolicyVersion", "delete payloadPolicyVersion", "missing payloadPolicyVersion", edit_json(lambda d: d.pop("payloadPolicyVersion")))
    record("bad_payloadLength", "payloadLength=201", "payloadLength", edit_json_rehash(lambda d: d.__setitem__("payloadLength", 201)))
    record("zero_totalFrames", "totalFrames=0", "totalFrames", edit_json_rehash(lambda d: d.__setitem__("totalFrames", 0)))
    record("bad_total_sum", "totalFrames does not equal shard sum", "totalFrames", edit_json_rehash(lambda d: d.__setitem__("totalFrames", d["totalFrames"] + 1)))
    record("zero_shardSize", "shardSize=0", "shardSize", edit_json_rehash(lambda d: d.__setitem__("shardSize", 0)))
    record("first_start_one", "first shard startFrame=1", "contiguous", edit_json_rehash(lambda d: d["shards"][0].__setitem__("startFrame", 1)))
    record("gap", "second shard startFrame += 1", "contiguous", edit_json_rehash(lambda d: d["shards"][1].__setitem__("startFrame", d["shards"][1]["startFrame"] + 1)))
    record("overlap", "second shard startFrame -= 1", "contiguous", edit_json_rehash(lambda d: d["shards"][1].__setitem__("startFrame", d["shards"][1]["startFrame"] - 1)))
    record("zero_shard_count", "shard frameCount=0", "frameCount", edit_json_rehash(lambda d: d["shards"][0].__setitem__("frameCount", 0)))
    record("duplicate_fileName", "duplicate shard fileName", "duplicate", edit_json_rehash(lambda d: d["shards"][1].__setitem__("fileName", d["shards"][0]["fileName"])))
    record("traversal_fileName", "../ in shard fileName", "unsafe", edit_json_rehash(lambda d: d["shards"][0].__setitem__("fileName", "../bad.bin")))
    record("wrong_shard_sha", "wrong shard sha", "SHA256", edit_json_rehash(lambda d: d["shards"][0].__setitem__("sha256", "0" * 64)))
    record("bad_shard_sha_len", "short shard sha", "sha256", edit_json(lambda d: d["shards"][0].__setitem__("sha256", "bad")))
    record("modify_shard_byte", "flip first shard byte", "SHA256", lambda p: flip_first_shard_byte(p))
    record("truncate_shard", "truncate shard", "size", lambda p: truncate_first_shard(p))
    record("extra_shard_byte", "append shard byte", "size", lambda p: append_first_shard_byte(p))
    record("delete_shard", "delete shard file", "missing shard", lambda p: delete_first_shard(p))
    record("bad_overallHash", "modify overallHash", "overallHash", edit_json(lambda d: d.__setitem__("overallHash", "0" * 64)))
    record("delete_overallHash", "delete overallHash", "missing overallHash", edit_json(lambda d: d.pop("overallHash")))
    record("bad_bit_order", "bitOrderWithinByte=msb_first", "bitOrderWithinByte", edit_json_rehash(lambda d: d.__setitem__("bitOrderWithinByte", "msb_first")))
    record("bad_bytes_per_frame", "bytesPerFrame wrong", "bytesPerFrame", edit_json_rehash(lambda d: d.__setitem__("bytesPerFrame", d["bytesPerFrame"] + 1)))

    try:
        read_frame_from_manifest(source_manifest, -1)
        actual = "NO_FAILURE"
        verdict = "FAIL"
    except Exception as exc:
        actual = str(exc)
        verdict = "PASS" if "frameIndex" in actual else "FAIL"
    rows.append({"testName": "negative_frame_index", "mutation": "frameIndex=-1", "expectedFailure": "frameIndex", "actualFailure": actual, "verdict": verdict})
    if verdict != "PASS":
        add_failure(failures, "negative frameIndex test failed")

    manifest = load_manifest(source_manifest)
    try:
        read_frame_from_manifest(source_manifest, manifest["totalFrames"])
        actual = "NO_FAILURE"
        verdict = "FAIL"
    except Exception as exc:
        actual = str(exc)
        verdict = "PASS" if "frameIndex" in actual else "FAIL"
    rows.append({"testName": "frame_index_total", "mutation": "frameIndex==totalFrames", "expectedFailure": "frameIndex", "actualFailure": actual, "verdict": verdict})
    if verdict != "PASS":
        add_failure(failures, "frameIndex==totalFrames test failed")

    repeat = run([
        sys.executable, "Task/Common/scripts/generate_common03_frame_pool.py", "--output-dir", str(source_manifest.parent.parent),
        "--master-seed", "2026072001", "--frame-count", "24", "--shard-size", "10", "--payload-length", "200",
    ], root)
    verdict = "PASS" if repeat.returncode != 0 and "overwrite" in (repeat.stderr + repeat.stdout) else "FAIL"
    rows.append({"testName": "repeat_without_overwrite", "mutation": "repeat generation without --overwrite", "expectedFailure": "overwrite", "actualFailure": repeat.stderr.strip() or repeat.stdout.strip(), "verdict": verdict})
    if verdict != "PASS":
        add_failure(failures, "repeat without overwrite negative test failed")

    output_path = root / STAGE_DIR / "negative_test_results.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["testName", "mutation", "expectedFailure", "actualFailure", "verdict"])
        writer.writeheader()
        writer.writerows(rows)


def first_shard_path(manifest_path: Path) -> Path:
    manifest = load_manifest(manifest_path)
    return manifest_path.parent / manifest["shards"][0]["fileName"]


def flip_first_shard_byte(manifest_path: Path) -> None:
    path = first_shard_path(manifest_path)
    data = bytearray(path.read_bytes())
    data[0] ^= 1
    path.write_bytes(data)


def truncate_first_shard(manifest_path: Path) -> None:
    path = first_shard_path(manifest_path)
    data = path.read_bytes()
    path.write_bytes(data[:-1])


def append_first_shard_byte(manifest_path: Path) -> None:
    path = first_shard_path(manifest_path)
    with path.open("ab") as handle:
        handle.write(b"\x00")


def delete_first_shard(manifest_path: Path) -> None:
    first_shard_path(manifest_path).unlink()


def check_no_later_stage_markers(root: Path, failures: list[str]) -> None:
    files = []
    for folder in [root / "Task/Common/include/common", root / "Task/Common/tests/stage03"]:
        if folder.exists():
            files.extend(path for path in folder.rglob("*") if path.is_file())
    files.extend(path for path in [root / "Task/Common/scripts/generate_common03_frame_pool.py", root / "Task/Common/scripts/build_common03.py"] if path.is_file())
    joined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in files)
    for marker in ["std::normal_distribution", "normal_distribution<", "awgnTransmit", "bpskModulate", "computeSigma", "llrValues[i]", "bitErrors /", "frameErrors /", "StopController", "resumeCheckpoint", "writeCheckpoint"]:
        if marker in joined:
            add_failure(failures, f"later-stage implementation marker found: {marker}")


def diff_name_status(root: Path, base: str, head: str) -> list[tuple[str, str]]:
    diff = run(["git", "diff", "--name-status", f"{base}...{head}"], root)
    if diff.returncode != 0:
        raise RuntimeError(diff.stderr.strip())
    entries = []
    for line in diff.stdout.splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2:
            entries.append((parts[0].strip(), parts[1].strip().replace("\\", "/")))
    return entries


def check_git_scope(root: Path, failures: list[str]) -> None:
    diff = run(["git", "diff", "--name-only", "main...HEAD"], root)
    if diff.returncode != 0:
        add_failure(failures, diff.stderr.strip())
        return
    for raw in diff.stdout.splitlines():
        path = raw.strip().replace("\\", "/")
        if path.startswith("Task/Common/Plan/") or path.startswith("Task/Common/build/"):
            add_failure(failures, f"generated or plan path committed: {path}")
        if path.startswith(("Task/BCH/", "Task/CC/", "Task/LDPC/")):
            add_failure(failures, f"out-of-scope path in committed diff: {path}")
        if path and not any(path.startswith(prefix) for prefix in ALLOWED_PREFIXES):
            add_failure(failures, f"path not allowed for Common-03 branch diff: {path}")


def git_blob_sha256(root: Path, commit: str, path: str) -> str:
    completed = run(["git", "show", f"{commit}:{path}"], root)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip())
    return hashlib.sha256(completed.stdout.encode("utf-8")).hexdigest()


def check_audit_files(root: Path, failures: list[str]) -> None:
    manifest_path = root / STAGE_DIR / "manifest.json"
    if not manifest_path.exists():
        return
    manifest = load_manifest(manifest_path)
    if "originalContentRange" not in manifest or "repairContentRange" not in manifest:
        return
    original = manifest["originalContentRange"]
    repair = manifest["repairContentRange"]
    original_entries = diff_name_status(root, original["baseCommit"], original["contentCommit"])
    repair_entries = diff_name_status(root, repair["baseCommit"], repair["contentCommit"])
    original_paths = sorted(path for _, path in original_entries)
    if original_paths != sorted(ORIGINAL_FUNCTIONAL_FILES):
        add_failure(failures, "original Common-03 functional range mismatch")
    repair_paths = sorted(path for _, path in repair_entries)
    expected_repair = sorted(manifest.get("repairContentFiles", []))
    if repair_paths != expected_repair:
        add_failure(failures, "repair Common-03 functional range mismatch")
    for path in sorted(set(original_paths + repair_paths)):
        if path.startswith("Task/Common/stages/stage03_common_frame_pool/"):
            add_failure(failures, "audit directory must not be counted as functional content")
    if manifest.get("remoteVerificationStatus") != "VERIFIED":
        add_failure(failures, "stage03 remoteVerificationStatus must be VERIFIED")
    if manifest.get("mergeStatus") != "NOT_MERGED":
        add_failure(failures, "stage03 mergeStatus must be NOT_MERGED")

    repair_commit = repair["contentCommit"]
    snapshot_pairs = {
        "Task/Common/include/common/frame_pool.hpp": root / STAGE_DIR / "snapshot/include/common/frame_pool.hpp",
        "Task/Common/include/common/sha256.hpp": root / STAGE_DIR / "snapshot/include/common/sha256.hpp",
        "Task/Common/scripts/build_common03.py": root / STAGE_DIR / "snapshot/scripts/build_common03.py",
        "Task/Common/scripts/check_common03.py": root / STAGE_DIR / "snapshot/scripts/check_common03.py",
        "Task/Common/scripts/generate_common03_frame_pool.py": root / STAGE_DIR / "snapshot/scripts/generate_common03_frame_pool.py",
        "Task/Common/tests/stage03/test_common03_frame_pool.cpp": root / STAGE_DIR / "snapshot/tests/stage03/test_common03_frame_pool.cpp",
    }
    for source_path, snapshot_path in snapshot_pairs.items():
        if not snapshot_path.exists():
            add_failure(failures, f"missing stage03 snapshot file: {snapshot_path}")
            continue
        try:
            expected = git_blob_sha256(root, repair_commit, source_path)
        except RuntimeError as exc:
            add_failure(failures, f"failed to read repair blob {source_path}: {exc}")
            continue
        if sha256_file(snapshot_path) != expected:
            add_failure(failures, f"stage03 snapshot mismatch: {source_path}")

    patch_path = root / STAGE_DIR / "changes.patch"
    patch_text = patch_path.read_text(encoding="utf-8", errors="ignore") if patch_path.exists() else ""
    if not patch_text.strip():
        add_failure(failures, "stage03 changes.patch must exist and be non-empty")
    if "diff --git a/Task/Common/stages/stage03_common_frame_pool/changes.patch" in patch_text:
        add_failure(failures, "stage03 changes.patch must not contain recursive diff")
    report = (root / STAGE_DIR / "validation_report.md").read_text(encoding="utf-8", errors="ignore")
    for forbidden in ["Pending", "to be run", "NOT_PUSHED", "TO_VERIFY_AFTER_PUSH"]:
        if forbidden in report:
            add_failure(failures, f"stage03 validation_report contains stale text: {forbidden}")


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    failures: list[str] = []
    manifests = check_generation(root, failures)
    check_golden_vectors(failures)
    if manifests:
        run_negative_tests(root, manifests[0], failures)
    check_cpp(root, manifests, failures)
    check_no_later_stage_markers(root, failures)
    check_audit_files(root, failures)
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
