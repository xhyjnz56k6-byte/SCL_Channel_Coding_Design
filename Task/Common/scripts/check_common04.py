#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path


STAGE_DIR = Path("Task/Common/stages/stage04_common_simulation_foundation")
TESTS = [
    ("G1", "PASS_COMMON_RANDOM_POLICY", "test_common04_random_policy.exe"),
    ("G2", "PASS_COMMON_GAUSSIAN_NOISE", "test_common04_gaussian_noise.exe"),
    ("G3", "PASS_COMMON_BPSK_AWGN_LLR", "test_common04_modulation_awgn.exe"),
    ("G4", "PASS_COMMON_METRICS_CONTROL", "test_common04_metrics_control.exe"),
    ("G5", "PASS_COMMON_CHECKPOINT_RESULTS", "test_common04_checkpoint.exe"),
    ("G6", "PASS_COMMON_INTEGRATION", "test_common04_integration.exe"),
]
FORBIDDEN_PREFIXES = ("Task/BCH/", "Task/CC/", "Task/LDPC/", "Task/Common/Plan/")


def run(command: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=root, text=True, capture_output=True)


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def run_or_fail(command: list[str], root: Path, label: str, failures: list[str]) -> None:
    result = run(command, root)
    if result.returncode:
        failures.append(f"{label}: {result.stdout}{result.stderr}")


def check_acceptance(root: Path, failures: list[str]) -> None:
    rows = list(csv.DictReader((root / STAGE_DIR / "acceptance_matrix.csv").open(encoding="utf-8")))
    ids = [row["requirementId"] for row in rows]
    require(len(rows) >= 46 and len(ids) == len(set(ids)), "acceptance matrix count or unique ids failed", failures)
    gates = {"PASS_COMMON_RANDOM_POLICY", "PASS_COMMON_GAUSSIAN_NOISE", "PASS_COMMON_BPSK_AWGN_LLR", "PASS_COMMON_METRICS_CONTROL", "PASS_COMMON_CHECKPOINT_RESULTS", "PASS_COMMON_INTEGRATION", "PASS_COMMON_SIMULATION_FOUNDATION"}
    seen = set()
    for row in rows:
        require(row.get("status") == "PASS", f"acceptance not PASS: {row['requirementId']}", failures)
        require(bool(row.get("evidence")) and row["evidence"].lower() not in {"planned", "todo"}, f"planned evidence: {row['requirementId']}", failures)
        require(row.get("gate") in gates, f"invalid gate: {row['requirementId']}", failures)
        seen.add(row.get("gate"))
    for gate in gates:
        require(gate in seen, f"no acceptance evidence for {gate}", failures)
    evidence = {row["requirementId"]: row["evidence"] for row in rows}
    required_evidence = {
        "G1-006": "compare_common04_cpp_python.py", "G3-006": "compare_common04_cpp_python.py",
        "G5-004": "test_common04_checkpoint.exe", "G5-006": "merge_common04_shards.py",
        "G6-001": "test_common04_integration.exe", "G6-004": "real_pool_smoke100",
        "G6-006": "formal_capacity_plan", "REG-001": "check_common02.py", "REG-002": "check_common03.py",
        "AUD-004": "manifest_functional_diff", "AUD-005": "remote_contains_functional_commit",
    }
    for requirement, token in required_evidence.items():
        require(token in evidence.get(requirement, ""), f"acceptance evidence missing {token}: {requirement}", failures)


def check_scope(root: Path, failures: list[str]) -> None:
    diff = run(["git", "diff", "--name-status", "main...HEAD"], root)
    for line in diff.stdout.splitlines():
        path = line.split("\t")[-1].replace("\\", "/")
        require(not path.startswith(FORBIDDEN_PREFIXES), f"forbidden path in diff: {path}", failures)
        require(not path.startswith(("Task/Common/build/", "Task/Common/results/")), f"generated path in diff: {path}", failures)
        require(not path.endswith((".exe", ".obj", ".pdb", ".pyc")), f"artifact in diff: {path}", failures)
    joined = ""
    for directory in [root / "Task/Common/include/common", root / "Task/Common/src", root / "Task/Common/tests/stage04"]:
        for path in directory.rglob("*"):
            if path.suffix in {".hpp", ".cpp", ".py"}:
                joined += path.read_text(encoding="utf-8", errors="ignore")
    for marker in ["std::normal_" + "distribution", "Vit" + "erbi", "Layered " + "BP", "inter" + "leave(", "deinter" + "leave("]:
        require(marker not in joined, f"forbidden implementation marker: {marker}", failures)


def check_manifest(root: Path, failures: list[str]) -> None:
    manifest = json.loads((root / STAGE_DIR / "manifest.json").read_text(encoding="utf-8"))
    base, functional = manifest.get("baseCommit"), manifest.get("functionalCommit")
    require(bool(base and functional), "manifest commits missing", failures)
    result = run(["git", "diff", "--name-status", f"{base}...{functional}"], root)
    expected = {"A": [], "M": [], "D": []}
    for line in result.stdout.splitlines():
        status, path = line.split("\t", 1)
        if status in expected:
            expected[status].append(path.replace("\\", "/"))
    require(sorted(manifest.get("added", [])) == sorted(expected["A"]), "manifest added mismatch", failures)
    require(sorted(manifest.get("modified", [])) == sorted(expected["M"]), "manifest modified mismatch", failures)
    require(sorted(manifest.get("deleted", [])) == sorted(expected["D"]), "manifest deleted mismatch", failures)
    require(manifest.get("remoteVerificationStatus") == "VERIFIED" and manifest.get("mergeStatus") == "NOT_MERGED", "manifest remote state mismatch", failures)
    remote = run(["git", "rev-parse", "--verify", manifest.get("remoteBranch", "")], root)
    require(remote.returncode == 0 and run(["git", "merge-base", "--is-ancestor", functional, remote.stdout.strip()], root).returncode == 0,
            "functional commit not on remote branch", failures)


def runner(root: Path, frame_manifest: Path, noise_manifest: Path, length: int, frames: int, ebn0: int, snr: int, decision: str,
           summary: Path, metadata: Path, failures: list[str]) -> None:
    command = [str(root / "Task/Common/build/stage04/common04_identity_runner.exe"), "--experiment", "common04_pool_backed",
               "--case", f"k{length}_{decision}", "--frame-manifest", str(frame_manifest), "--noise-manifest", str(noise_manifest),
               "--payload-length", str(length), "--frame-start", "0", "--frame-count", str(frames), "--ebn0", str(ebn0),
               "--snr-index", str(snr), "--decision", decision, "--summary", str(summary), "--metadata", str(metadata)]
    run_or_fail(command, root, f"runner k{length} {decision} {ebn0}", failures)


def validate_summary(summary: Path, frame_count: int, failures: list[str]) -> list[dict[str, str]]:
    rows = list(csv.DictReader(summary.open(encoding="utf-8")))
    require(bool(rows), "real summary is empty", failures)
    for row in rows:
        processed, bits = int(row["processedFrames"]), int(row["totalPayloadBits"])
        errors, frame_errors, successes = int(row["bitErrors"]), int(row["frameErrors"]), int(row["successfulFrames"])
        require(processed == frame_count and bits == processed * int(row["payloadLength"]), "summary count mismatch", failures)
        require(successes + frame_errors == processed, "summary success/frame error mismatch", failures)
        require(abs(float(row["ber"]) - errors / bits) < 1e-6, "summary BER mismatch", failures)
        require(abs(float(row["fer"]) - frame_errors / processed) < 1e-6, "summary FER mismatch", failures)
        require(abs(float(row["successRate"]) - successes / processed) < 1e-6, "summary success rate mismatch", failures)
        require(row["payloadLength"] == row["encodedLength"] and float(row["codeRate"]) == 1.0, "identity baseline must be R=1", failures)
    return rows


def check_python_merge(root: Path, failures: list[str]) -> None:
    directory = root / "Task/Common/build/stage04/python_merge"
    directory.mkdir(parents=True, exist_ok=True)
    fields = ["schemaVersion", "experimentId", "stage", "codeType", "caseName", "payloadLength", "encodedLength", "ebN0_dB", "snrIndex", "framePoolId", "noisePoolId", "configHash", "shardIndex", "frameStart", "frameCount", "processedFrames", "totalPayloadBits", "bitErrors", "frameErrors", "successfulFrames", "encodeTimeNsSum", "channelTimeNsSum", "decodeTimeNsSum", "recoveryTimeNsSum", "totalTimeNsSum", "maxDecodeTimeNs", "maxTotalTimeNs"]
    def row(index: int, start: int, count: int) -> dict[str, str]:
        return {"schemaVersion": "common04.result_summary.v1", "experimentId": "merge", "stage": "stage04_common_simulation_foundation", "codeType": "IDENTITY", "caseName": "k200", "payloadLength": "200", "encodedLength": "200", "ebN0_dB": "2", "snrIndex": "1", "framePoolId": "frame", "noisePoolId": "noise", "configHash": "hash", "shardIndex": str(index), "frameStart": str(start), "frameCount": str(count), "processedFrames": str(count), "totalPayloadBits": str(count * 200), "bitErrors": str(count), "frameErrors": str(count), "successfulFrames": "0", "encodeTimeNsSum": str(count * 10), "channelTimeNsSum": str(count * 20), "decodeTimeNsSum": str(count * 30), "recoveryTimeNsSum": str(count * 40), "totalTimeNsSum": str(count * 100), "maxDecodeTimeNs": str(30 + index), "maxTotalTimeNs": str(100 + index)}
    def write(name: str, data: dict[str, str]) -> Path:
        path = directory / name
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerow(data)
        return path
    first, second = write("shard0.csv", row(0, 0, 40)), write("shard1.csv", row(1, 40, 60))
    merged = directory / "merged.csv"
    run_or_fail([sys.executable, "Task/Common/scripts/merge_common04_shards.py", "--output", str(merged), str(first), str(second)], root, "python shard merge positive", failures)
    if merged.exists():
        result = next(csv.DictReader(merged.open(encoding="utf-8")))
        require(result["frameCount"] == "100" and result["totalTimeNsSum"] == "10000" and result["maxTotalTimeNs"] == "101", "python shard merge latency aggregation failed", failures)
        require(abs(float(result["avgTotalTimeUs"]) - 0.1) < 1e-12, "python shard merge average latency failed", failures)
        cpp_reference = {row["field"]: row["value"] for row in csv.DictReader((root / "Task/Common/build/stage04/cpp_reference_runtime.csv").open(encoding="utf-8"))}
        for python_field, cpp_field in [("processedFrames", "cxxMergeProcessedFrames"), ("totalPayloadBits", "cxxMergeTotalPayloadBits"),
                                        ("bitErrors", "cxxMergeBitErrors"), ("frameErrors", "cxxMergeFrameErrors"),
                                        ("totalTimeNsSum", "cxxMergeTotalTimeNsSum"), ("maxTotalTimeNs", "cxxMergeMaxTotalTimeNs")]:
            require(result[python_field] == cpp_reference.get(cpp_field), f"C++/Python shard merge mismatch: {python_field}", failures)
    for name, mutate in [("gap", lambda value: value.update(frameStart="41")), ("duplicate", lambda value: value.update(shardIndex="0")), ("bad_total", lambda value: value.update(totalPayloadBits="1"))]:
        bad = row(1, 40, 60); mutate(bad)
        path = write(f"{name}.csv", bad)
        result = run([sys.executable, "Task/Common/scripts/merge_common04_shards.py", "--output", str(directory / f"{name}_out.csv"), str(first), str(path)], root)
        require(result.returncode != 0, f"python shard merge negative failed: {name}", failures)
    missing = directory / "missing_latency.csv"
    with missing.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[field for field in fields if field != "totalTimeNsSum"])
        writer.writeheader(); writer.writerow({key: value for key, value in row(1, 40, 60).items() if key != "totalTimeNsSum"})
    result = run([sys.executable, "Task/Common/scripts/merge_common04_shards.py", "--output", str(directory / "missing_latency_out.csv"), str(first), str(missing)], root)
    require(result.returncode != 0, "python shard merge missing latency negative failed", failures)


def check_formal_capacity(root: Path, failures: list[str]) -> None:
    config = json.loads((root / "Task/Common/config/common04_formal_template.json").read_text(encoding="utf-8"))
    frames, symbols, per_shard = config["frames"], config["symbolsPerFrame"], config["framesPerShard"]
    expected = math.ceil(frames / per_shard)
    require((frames, symbols, per_shard, config["expectedShardCount"]) == (50000, 1000, 1000, 50), "formal capacity config mismatch", failures)
    require(expected == 50 and frames - 1 == 49999 and (expected - 1) * per_shard == 49000, "formal capacity range mismatch", failures)
    require(frames * symbols * 8 == 400000000, "formal capacity byte calculation mismatch", failures)
    require(all(min(per_shard, frames - index * per_shard) > 0 for index in range(expected)), "formal shard plan invalid", failures)


def run_pool_campaign(root: Path, label: str, frames: int, ebn0s: list[int], pool_dir: Path, failures: list[str]) -> None:
    frame_dir = pool_dir / "frames"
    noise_dir = pool_dir / "noise"
    run_or_fail([sys.executable, "Task/Common/scripts/generate_common03_frame_pool.py", "--output-dir", str(frame_dir),
                 "--frame-count", str(frames), "--shard-size", "25", "--payload-length", "200", "300", "--overwrite"], root, "frame pool generation", failures)
    run_or_fail([sys.executable, "Task/Common/scripts/generate_common04_noise_pool.py", "--output-dir", str(noise_dir),
                 "--frame-count", str(frames), "--symbols-per-frame", "300", "--frames-per-shard", "25", "--overwrite"], root, "noise pool generation", failures)
    noise_manifest = noise_dir / "manifest.json"
    run_or_fail([sys.executable, "Task/Common/scripts/validate_common04_noise_pool.py", str(noise_manifest)], root, "noise pool validation", failures)
    summary, metadata = pool_dir / "summary.csv", pool_dir / "metadata.json"
    for length in [200, 300]:
        for decision in ["HARD", "LLR_SIGN"]:
            for snr, ebn0 in enumerate(ebn0s):
                runner(root, frame_dir / f"k{length}" / "manifest.json", noise_manifest, length, frames, ebn0, snr, decision, summary, metadata, failures)
    rows = validate_summary(summary, frames, failures)
    for length in [200, 300]:
        for snr in range(len(ebn0s)):
            hard = next(row for row in rows if row["caseName"] == f"k{length}_HARD" and int(row["snrIndex"]) == snr)
            llr = next(row for row in rows if row["caseName"] == f"k{length}_LLR_SIGN" and int(row["snrIndex"]) == snr)
            require((hard["bitErrors"], hard["frameErrors"]) == (llr["bitErrors"], llr["frameErrors"]), "HARD/LLR decision mismatch", failures)
        series = [float(next(row for row in rows if row["caseName"] == f"k{length}_HARD" and int(row["snrIndex"]) == index)["ber"]) for index in range(len(ebn0s))]
        require(series[-1] <= series[0], "gross high-SNR BER trend failed", failures)
    data = json.loads(metadata.read_text(encoding="utf-8"))
    require(data["framePoolId"] != "generated" and data["noisePoolId"] != "generated" and "createdTime" in data, "pool metadata identity missing", failures)
    require("runtime_metadata_only" not in data["configHash"], "createdTime leaked into configHash", failures)
    plot_dir = pool_dir / "plots"
    run_or_fail([sys.executable, "Task/Common/scripts/plot_common_results.py", "--input", str(summary), "--output-dir", str(plot_dir)], root, "plotting", failures)
    for path in plot_dir.glob("*.png"):
        require(path.stat().st_size > 100, f"empty plot: {path.name}", failures)
    require(len(list(plot_dir.glob("*.png"))) == 6, "plot count mismatch", failures)


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    failures: list[str] = []
    build = run([sys.executable, "Task/Common/scripts/build_common04.py"], root)
    if build.returncode:
        failures.append(build.stdout + build.stderr)
    for name, gate, executable in TESTS:
        result = run([str(root / "Task/Common/build/stage04" / executable)], root)
        if result.returncode:
            failures.append(f"{name}: {result.stdout}{result.stderr}")
        else:
            print(f"COMMON-04 {name} CHECK: PASS\nGate: {gate}")
    compare = run([sys.executable, "Task/Common/scripts/compare_common04_cpp_python.py"], root)
    require(compare.returncode == 0 and "mismatchCount=0" in compare.stdout, f"C++/Python comparison failed: {compare.stdout}{compare.stderr}", failures)
    check_python_merge(root, failures)
    output = root / "Task/Common/build/stage04/real_pool_runs"
    if output.exists():
        shutil.rmtree(output)
    run_pool_campaign(root, "smoke", 100, [0, 2, 4], output / "smoke", failures)
    run_pool_campaign(root, "prescan", 2000, list(range(7)), output / "prescan", failures)
    check_formal_capacity(root, failures)
    check_scope(root, failures)
    check_acceptance(root, failures)
    check_manifest(root, failures)
    for script, token in [("Task/Common/scripts/check_common02.py", "COMMON-02 CHECK: PASS"), ("Task/Common/scripts/check_common03.py", "COMMON-03 CHECK: PASS")]:
        result = run([sys.executable, script], root)
        require(result.returncode == 0 and token in result.stdout, f"regression failed: {script}\n{result.stdout}{result.stderr}", failures)
    if failures:
        print("COMMON-04 CHECK: FAIL")
        for failure in failures:
            print("- " + failure)
        return 1
    print("COMMON-04 CHECK: PASS\nGate: PASS_COMMON_SIMULATION_FOUNDATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
