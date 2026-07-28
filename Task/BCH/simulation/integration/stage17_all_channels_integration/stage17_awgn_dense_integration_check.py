#!/usr/bin/env python3
import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
STAGE07 = ROOT / "Task" / "BCH" / "simulation" / "stages" / "S2" / "stage07_awgn_dense_formal"
RESULTS = STAGE07 / "results"
PLOTS = STAGE07 / "plots"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
CASES = [
    "K200_S15", "K200_M255K207", "K200_M511K421", "K200_M511K385",
    "K300_S15", "K300_M255K207", "K300_M511K421", "K300_M511K385",
]


def fail(message):
    raise SystemExit("BLOCKED_STAGE17_AWGN_DENSE_INTEGRATION_CHECK: " + message)


def req(value, message):
    if not value:
        fail(message)


def git(*args, check=True):
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and proc.returncode != 0:
        fail(proc.stderr.strip() or "git command failed: " + " ".join(args))
    return proc


def ancestor(commit, ref="HEAD"):
    return git("merge-base", "--is-ancestor", commit, ref, check=False).returncode == 0


def rows(path):
    req(path.exists() and path.stat().st_size > 0, "missing CSV: " + str(path))
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(a, b, tol=1e-10):
    return math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol)


def check_results(data):
    req(len(data) == 296, "formal results row count is not 296")
    req(set(r["caseId"] for r in data) == set(CASES), "case set mismatch")
    expected_grid = [round(i * 0.5, 1) for i in range(37)]
    for case_id in CASES:
        pts = [r for r in data if r["caseId"] == case_id]
        req(len(pts) == 37, case_id + " does not have 37 points")
        req([int(r["snrIndex"]) for r in pts] == list(range(37)), case_id + " snrIndex mismatch")
        req([round(float(r["snrDb"]), 1) for r in pts] == expected_grid, case_id + " SNR grid mismatch")
    seen = set()
    for r in data:
        key = (r["caseId"], int(r["snrIndex"]))
        req(key not in seen, "duplicate result point")
        seen.add(key)
        rate = int(r["payloadLength"]) / int(r["encodedLength"])
        snr_db = float(r["snrDb"])
        snr_linear = 10.0 ** (snr_db / 10.0)
        ebn0_db = snr_db - 10.0 * math.log10(2.0 * rate)
        sigma2 = 1.0 / snr_linear
        req(close(r["actualRate"], rate), "actualRate mismatch")
        req(close(r["snrLinear"], snr_linear), "snrLinear mismatch")
        req(close(r["ebn0Db"], ebn0_db), "Eb/N0 mismatch")
        req(close(r["sigma2"], sigma2), "sigma2 mismatch")
        frames = int(r["totalFrames"])
        frame_errors = int(r["payloadErrorFrames"])
        payload_bits = int(r["totalPayloadBits"])
        bit_errors = int(r["payloadErrorBits"])
        req(1000 <= frames <= 50000, "frame count outside stop range")
        if r["stopReason"] == "TARGET_FRAME_ERRORS_REACHED":
            req(frame_errors >= 200, "target stop without enough frame errors")
        elif r["stopReason"] == "MAX_FRAMES_REACHED":
            req(frames == 50000 and frame_errors < 200, "max-frame stop invalid")
        else:
            fail("unknown stopReason: " + r["stopReason"])
        req(payload_bits == frames * int(r["payloadLength"]), "totalPayloadBits mismatch")
        req(close(r["ber"], bit_errors / payload_bits), "BER recompute mismatch")
        req(close(r["fer"], frame_errors / frames), "FER recompute mismatch")
        for field, value in r.items():
            if field in {
                "snrLinear", "ebn0Db", "sigma2", "actualRate", "ber", "fer",
                "decoderFailureRate", "miscorrectionRate", "undetectedErrorRate",
                "trueSuccessRate", "encodeTimeMeanNs", "decodeTimeMeanNs",
                "decodeTimeP50Ns", "decodeTimeP95Ns", "decodeTimeP99Ns", "decodeTimeMaxNs",
            }:
                req(math.isfinite(float(value)), "NaN or Inf in " + field)
        for field in (
            "totalFrames", "totalPayloadBits", "payloadErrorBits", "payloadErrorFrames",
            "decoderFailureFrames", "miscorrectionFrames", "undetectedErrorFrames",
            "trueSuccessFrames", "encodeTimeTotalNs", "decodeTimeTotalNs",
        ):
            req(int(r[field]) >= 0, "negative counter: " + field)
        git_commit = r.get("gitCommit", "")
        req(git_commit and ancestor(git_commit), "result gitCommit not traceable")


def check_progress(data):
    progress = rows(RESULTS / "stage07_awgn_dense_formal_progress.csv")
    req(len(progress) == 296, "progress row count mismatch")
    req(all(r["status"] == "COMPLETE" for r in progress), "progress contains non-COMPLETE point")
    result_points = {(r["caseId"], r["snrIndex"]) for r in data}
    progress_points = {(r["caseId"], r["snrIndex"]) for r in progress}
    req(result_points == progress_points, "progress point set mismatch")


def check_figures():
    manifest_path = PLOTS / "stage07_awgn_dense_formal_plot_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results = RESULTS / manifest["sourceResultsFile"]
    req(manifest["sourceResultsSha256"] == sha256(results), "source results hash mismatch")
    aggregate = PLOTS / manifest["aggregateFigureData"]
    req(manifest["aggregateFigureDataSha256"] == sha256(aggregate), "aggregate figure-data hash mismatch")
    req(len(manifest["figures"]) == 6, "figure count mismatch")
    for fig in manifest["figures"]:
        png = PLOTS / fig["png"]
        fig_data = PLOTS / fig["figureData"]
        req(png.exists(), "missing PNG: " + fig["png"])
        req(png.read_bytes()[:8] == PNG_MAGIC, "PNG magic mismatch: " + fig["png"])
        req(fig["pngSha256"] == sha256(png), "PNG hash mismatch: " + fig["png"])
        req(fig["figureDataSha256"] == sha256(fig_data), "figure-data hash mismatch: " + fig["figureData"])
        data = rows(fig_data)
        req(len({r["caseId"] for r in data}) == 4, "figure does not contain 4 cases: " + fig["figureId"])
    commit = manifest.get("gitCommit", "")
    req(commit and ancestor(commit), "plot manifest gitCommit not traceable")


def check_manifest():
    manifest = json.loads((STAGE07 / "stage07_awgn_dense_formal_manifest.json").read_text(encoding="utf-8"))
    req(manifest["gate"] == "PASS_STAGE07_AWGN_DENSE_FORMAL", "manifest gate mismatch")
    req(manifest["overallGate"] == "PASS_BCH_S2_AWGN_DENSE_RERUN", "manifest overall gate mismatch")


def check_ephemeral_points():
    point_files = list((RESULTS / "points").glob("*")) if (RESULTS / "points").exists() else []
    if not point_files:
        print("EPHEMERAL_POINT_EVIDENCE_NOT_TRACKED_AS_DESIGNED")


def main():
    check_manifest()
    data = rows(RESULTS / "stage07_awgn_dense_formal_results.csv")
    check_results(data)
    check_progress(data)
    check_figures()
    check_ephemeral_points()
    print("PASS_STAGE17_AWGN_DENSE_INTEGRATION_CHECK")


if __name__ == "__main__":
    main()
