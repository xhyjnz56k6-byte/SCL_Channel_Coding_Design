#!/usr/bin/env python3
import csv
import json
import math
import pathlib
import sys


def fail(message: str) -> None:
    raise RuntimeError(message)


def check_fixed(root: pathlib.Path) -> None:
    config_path = pathlib.Path(__file__).resolve().parents[1] / "config" / "s5_smoke_frozen_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    payload_config = config["payload"]
    noise_config = config["noise"]
    if payload_config != {
        "length": 300,
        "framePoolId": "payload_k300_seed2026072001_policy1_frames100",
        "framePoolOverallHash": "83880398af81a8385d1dbd7e6870554311a0bb7d96ddeb5d3434b06a68a2005f",
        "masterSeed": 2026072001,
        "policyVersion": 1,
    }:
        fail("frozen frame-pool identity mismatch")
    if noise_config["strategy"] != "s5_complex_pair_v1" or noise_config["masterSeed"] != 2026072004:
        fail("frozen noise identity mismatch")
    repo_root = pathlib.Path(__file__).resolve().parents[5]
    manifest_path = repo_root / "Task" / "Common" / "build" / "stage04" / "real_pool_runs" / "smoke" / "frames" / "k300" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["framePoolId"] != payload_config["framePoolId"] or manifest["overallHash"] != payload_config["framePoolOverallHash"]:
        fail("Common frame-pool manifest identity mismatch")
    shard = manifest["shards"][0]
    packed = (manifest_path.parent / shard["fileName"]).read_bytes()
    summary = list(csv.DictReader((root / "fixed_vector_summary.csv").open(encoding="utf-8")))
    trace = list(csv.DictReader((root / "fixed_vector_trace.csv").open(encoding="utf-8")))
    codec_rows = list(csv.DictReader((root / "fixed_codec_bits.csv").open(encoding="utf-8")))
    if len(summary) != 2160:
        fail(f"fixed summary row count {len(summary)} != 2160")
    if not trace:
        fail("fixed trace is empty")
    fixture_payload = {}
    for row in codec_rows:
        if row["scheme"] == "CC_R12_BLOCK_FLOAT" and row["kind"] == "payload":
            fixture_payload.setdefault(int(row["frameIndex"]), []).append((int(row["bitIndex"]), int(row["bit"])))
    for frame in range(10):
        expected = [((packed[frame * 38 + bit // 8] >> (bit % 8)) & 1) for bit in range(300)]
        actual = [value for _, value in sorted(fixture_payload[frame])]
        if actual != expected:
            fail(f"fixed payload differs from Common frame pool at frame {frame}")
    for row in summary:
        if row["mode"] == "NO_IMPAIRMENT_NO_NOISE" and int(row["bitErrors"]) != 0:
            fail("noiseless identity decode mismatch")
    relative_starts = {}
    for row in summary:
        if row["channel"] not in {"KNOWN_BLOCKAGE_10_PERCENT", "UNKNOWN_BURST_5_PERCENT_ISR_10DB"}:
            continue
        key = (row["channel"], row["mode"], row["esN0Db"], row["frameIndex"])
        relative_starts.setdefault(key, set()).add(row["relativeStart"])
    if any(len(values) != 1 for values in relative_starts.values()):
        fail("same-frame relative damage start mismatch across schemes")
    ntx = {459, 480, 612, 640}
    seen_phase_lengths = set()
    for row in trace:
        values = [float(row[k]) for k in ("rxReal", "rxImag", "llr", "sigmaSquared")]
        if not all(math.isfinite(x) for x in values):
            fail("NaN/Inf in fixed trace")
        if row["channel"] == "KNOWN_BLOCKAGE_10_PERCENT" and float(row["mask"]) == 0.0:
            if float(row["llr"]) != 0.0:
                fail("blocked symbol LLR is not zero")
        if row["channel"] == "LINEAR_TIME_VARYING_FREQUENCY":
            seen_phase_lengths.add(row["scheme"])
    if len(seen_phase_lengths) != 4:
        fail("complete Doppler phase traces missing for one or more Ntx")
    cc_lengths = {(row["scheme"], int(row["frameIndex"])) for row in codec_rows
                  if row["kind"] == "transmitted"}
    if not any(scheme == "CC_R23_BLOCK_FLOAT" for scheme, _ in cc_lengths):
        fail("CC R2/3 punctured transmitted fixture missing")
    blockage_counts = {}
    for row in trace:
        if row["channel"] != "KNOWN_BLOCKAGE_10_PERCENT":
            continue
        key = (row["scheme"], row["mode"], row["esN0Db"], row["frameIndex"])
        if float(row["mask"]) == 0.0:
            blockage_counts[key] = blockage_counts.get(key, 0) + 1
    for row in summary:
        if row["channel"] != "KNOWN_BLOCKAGE_10_PERCENT" or row["mode"] == "NO_IMPAIRMENT_NO_NOISE":
            continue
        key = (row["scheme"], row["mode"], row["esN0Db"], row["frameIndex"])
        if blockage_counts.get(key, 0) != int(row["damageLength"]):
            fail(f"puncture/blockage transmitted-domain mask mismatch: {key}")
    print("PASS_S5_FIXED_CHECKER")


def check_grid(root: pathlib.Path) -> None:
    rows = list(csv.DictReader((root / "grid_smoke_summary.csv").open(encoding="utf-8")))
    if len(rows) not in {12, 44, 264}:
        fail(f"unexpected grid row count {len(rows)}")
    keys = set()
    paired = {}
    for row in rows:
        key = (row["group"], row["channel"], row["esN0Db"], row["scheme"])
        if key in keys:
            fail(f"duplicate scheme point: {key}")
        keys.add(key)
        numeric = [float(row[k]) for k in ("BER", "FER", "avgChannelProcessingTimeUs",
                                           "p95ChannelProcessingTimeUs", "avgDecodeTimeUs",
                                           "p95DecodeTimeUs", "avgTotalReceiverAlgorithmTimeUs",
                                           "p95TotalReceiverAlgorithmTimeUs")]
        if not all(math.isfinite(x) for x in numeric):
            fail(f"NaN/Inf in grid row: {key}")
        frames = int(row["frames"])
        if frames < 1000 or frames > 50000:
            fail(f"frame count outside frozen range: {key}")
        expected_ber = int(row["payloadBitErrors"]) / (frames * 300)
        expected_fer = int(row["frameErrors"]) / frames
        if abs(float(row["BER"]) - expected_ber) > 5e-6 or abs(float(row["FER"]) - expected_fer) > 5e-6:
            fail(f"BER/FER count inconsistency: {key}")
        reason = row["pairedStopReason"]
        if reason == "PAIRED_TARGET_FRAME_ERRORS_REACHED" and int(row["frameErrors"]) < 200:
            fail(f"invalid paired target stop: {key}")
        if reason not in {"PAIRED_TARGET_FRAME_ERRORS_REACHED", "PAIRED_MAX_FRAMES_REACHED"}:
            fail(f"invalid paired stop reason: {key}")
        if row["iterationsApplicable"] == "false":
            for field in ("avgIterations", "p95Iterations", "maxIterations", "maxIterationFrames", "maxIterationRate"):
                if row[field] != "NA":
                    fail(f"CC iteration field must be NA: {key}/{field}")
        elif not all(math.isfinite(float(row[field])) for field in
                     ("avgIterations", "p95Iterations", "maxIterations", "maxIterationFrames", "maxIterationRate")):
            fail(f"invalid LDPC iteration field: {key}")
        pair_key = key[:3]
        paired.setdefault(pair_key, []).append(frames)
    for key, counts in paired.items():
        if len(counts) != 2 or counts[0] != counts[1]:
            fail(f"paired stopping mismatch: {key} -> {counts}")
    print("PASS_S5_GRID_CHECKER")


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in {"fixed", "grid"}:
        print("usage: check_s5_results.py fixed|grid RESULT_DIR", file=sys.stderr)
        return 2
    root = pathlib.Path(sys.argv[2])
    (check_fixed if sys.argv[1] == "fixed" else check_grid)(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
