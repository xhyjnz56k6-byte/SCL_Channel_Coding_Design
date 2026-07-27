import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
STAGE = Path(__file__).resolve().parents[1]
RESULTS = STAGE / "results"
LOGS = STAGE / "logs"
PLOTS = STAGE / "plots"
PUBLISHED = STAGE / "published_results"
CONFIG = STAGE / "configs/stage07_awgn_dense_formal_config.json"
STAGE06 = ROOT / "Task/BCH/simulation/stages/S2/stage06_awgn_formal/results/stage06_awgn_formal_results.csv"
CASES = [
    "K200_S15", "K200_M255K207", "K200_M511K421", "K200_M511K385",
    "K300_S15", "K300_M255K207", "K300_M511K421", "K300_M511K385",
]
STYLE_IDS = {"STYLE_1", "STYLE_2", "STYLE_3", "STYLE_4"}
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def rows(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, data, fieldnames=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(data[0]) if data else []
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def req(value, message):
    if not value:
        raise SystemExit("BLOCKED_STAGE07_AWGN_DENSE_FORMAL_CHECK: " + message)


def close(a, b, tol=1e-10):
    return math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol)


def row_sha(row):
    payload = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def expected_grid():
    return [round(i * 0.5, 1) for i in range(37)]


def check_config_and_results(data):
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    req(config["stageId"] == "stage07_awgn_dense_formal", "stageId mismatch")
    req(config["waveformSnrGridDb"] == {"start": 0.0, "stop": 18.0, "step": 0.5, "inclusive": True},
        "SNR grid config mismatch")
    req(config["stopRule"] == {"minFrames": 1000, "targetFrameErrors": 200, "maxFrames": 50000},
        "stop rule mismatch")
    req(config["checkpointEveryFrames"] == 1000, "checkpoint interval mismatch")
    req(len(data) == 296, "results row count is not 296")
    seen = set()
    grid = expected_grid()
    for case_id in CASES:
        pts = [r for r in data if r["caseId"] == case_id]
        req(len(pts) == 37, f"{case_id} does not have 37 points")
        req([int(r["snrIndex"]) for r in pts] == list(range(37)), f"{case_id} snrIndex mismatch")
        req([round(float(r["snrDb"]), 1) for r in pts] == grid, f"{case_id} snrDb grid mismatch")
    for r in data:
        key = (r["caseId"], int(r["snrIndex"]))
        req(key not in seen, "duplicate point")
        seen.add(key)
        req(r["stageId"] == "stage07_awgn_dense_formal", "result stageId mismatch")
        req(r["caseId"] in CASES, "unknown case")
        req(r["styleId"] in STYLE_IDS, "unknown style")
        rate = float(r["actualRate"])
        snr_db = float(r["snrDb"])
        snr_linear = 10.0 ** (snr_db / 10.0)
        ebn0_db = snr_db - 10.0 * math.log10(2.0 * rate)
        sigma_snr = 1.0 / snr_linear
        sigma_ebn0 = 1.0 / (2.0 * rate * 10.0 ** (ebn0_db / 10.0))
        req(close(r["actualRate"], int(r["payloadLength"]) / int(r["encodedLength"])), "actualRate mismatch")
        req(close(r["snrLinear"], snr_linear), "snrLinear mismatch")
        req(close(r["ebn0Db"], ebn0_db), "ebn0Db mismatch")
        req(close(r["sigma2"], sigma_snr) and close(r["sigma2"], sigma_ebn0), "sigma2 mismatch")
        f = int(r["totalFrames"])
        e = int(r["payloadErrorFrames"])
        bits = int(r["totalPayloadBits"])
        bit_errors = int(r["payloadErrorBits"])
        req(1000 <= f <= 50000, "frame count outside stop range")
        if r["stopReason"] == "TARGET_FRAME_ERRORS_REACHED":
            req(e >= 200, "target stop without target frame errors")
        elif r["stopReason"] == "MAX_FRAMES_REACHED":
            req(f == 50000 and e < 200, "max-frame stop invalid")
        else:
            req(False, "unknown stopReason")
        req(int(r["trueSuccessFrames"]) + e == f, "trueSuccess + errors != frames")
        req(bits == f * int(r["payloadLength"]), "totalPayloadBits mismatch")
        req(close(r["ber"], bit_errors / bits), "BER cannot be recomputed")
        req(close(r["fer"], e / f), "FER cannot be recomputed")
        req(all(int(r[x]) >= 0 for x in (
            "totalFrames", "totalPayloadBits", "payloadErrorBits", "payloadErrorFrames",
            "decoderFailureFrames", "miscorrectionFrames", "undetectedErrorFrames",
            "trueSuccessFrames", "noiseChecksum")), "negative integer counter")
        req(all(math.isfinite(float(r[x])) for x in (
            "ber", "fer", "decoderFailureRate", "miscorrectionRate", "undetectedErrorRate",
            "trueSuccessRate", "decodeTimeMeanNs", "decodeTimeP99Ns")), "NaN or Inf")


def check_points_and_progress(data):
    checkpoint_count = len(list((RESULTS / "points").glob("*/*/*.json")))
    point_csv_count = len(list((RESULTS / "points").glob("*/*/*_result.csv")))
    point_log_count = len(list((RESULTS / "points").glob("*/*/*_run.log")))
    req(checkpoint_count == 296, "checkpoint count mismatch")
    req(point_csv_count == 296, "point result CSV count mismatch")
    req(point_log_count == 296, "point log count mismatch")
    progress = rows(RESULTS / "stage07_awgn_dense_formal_progress.csv")
    req(len(progress) == 296, "progress row count mismatch")
    req(all(r["status"] == "COMPLETE" for r in progress), "not all progress points complete")
    req({(r["caseId"], r["snrIndex"]) for r in progress} ==
        {(r["caseId"], r["snrIndex"]) for r in data}, "progress points mismatch")


def check_figures(data):
    manifest = json.loads((PLOTS / "stage07_awgn_dense_formal_plot_manifest.json").read_text(encoding="utf-8"))
    req(manifest["stageId"] == "stage07_awgn_dense_formal", "plot manifest stage mismatch")
    req(manifest["sourceResultsSha256"] == sha(RESULTS / manifest["sourceResultsFile"]),
        "source results hash mismatch")
    req(manifest["plotScriptSha256"] == sha(STAGE / "python" / manifest["plotScript"]),
        "plot script hash mismatch")
    req(manifest["configSha256"] == sha(CONFIG), "config hash mismatch")
    aggregate = rows(PLOTS / manifest["aggregateFigureData"])
    req(len(aggregate) == 888, "aggregate figure-data row count mismatch")
    req(manifest["aggregateFigureDataSha256"] == sha(PLOTS / manifest["aggregateFigureData"]),
        "aggregate figure-data hash mismatch")
    source_by_id = {str(i + 1): r for i, r in enumerate(data)}
    req(len(manifest["figures"]) == 6, "figure count mismatch")
    forbidden = list(PLOTS.glob("*.pdf")) + list(PLOTS.glob("*.svg")) + list(PLOTS.glob("*.eps")) + \
        list(PLOTS.glob("*.jpg")) + list(PLOTS.glob("*.jpeg"))
    req(not forbidden, "forbidden plot format exists")
    for fig in manifest["figures"]:
        png = PLOTS / fig["png"]
        req(png.read_bytes()[:8] == PNG_MAGIC, "PNG header mismatch")
        req(fig["pngSha256"] == sha(png), "PNG hash mismatch")
        req(fig["dpi"] == 300 and fig["imageFormat"] == "png", "PNG contract mismatch")
        req(fig["xLabel"] == "SNR (dB)" and fig["xMin"] == 0.0 and fig["xMax"] == 18.0 and fig["xStep"] == 0.5,
            "x-axis contract mismatch")
        req(fig["legendLocation"] == "upper right", "legend location mismatch")
        req(fig["yScale"] in ("log", "linear"), "unknown y scale")
        fd = rows(PLOTS / fig["figureData"])
        req(len(fd) == 148, "per-figure data row count mismatch")
        req(fig["figureDataSha256"] == sha(PLOTS / fig["figureData"]), "figure-data hash mismatch")
        req(len({r["caseId"] for r in fd}) == 4, "figure does not contain 4 cases")
        for r in fd:
            source = source_by_id[r["sourceRowId"]]
            req(r["sourceRowSha256"] == row_sha(source), "source row hash mismatch")
            req(r["rawY"] == (f"{float(source[r['metric']]):.17g}" if r["metric"] in ("ber", "fer")
                              else f"{float(source['decodeTimeMeanNs']) / 1000.0:.17g}"),
                "rawY mismatch")
            if r["metric"] == "ber":
                req(int(r["rawNumerator"]) == int(source["payloadErrorBits"]), "BER numerator mismatch")
                req(int(r["rawDenominator"]) == int(source["totalPayloadBits"]), "BER denominator mismatch")
            if r["metric"] == "fer":
                req(int(r["rawNumerator"]) == int(source["payloadErrorFrames"]), "FER numerator mismatch")
                req(int(r["rawDenominator"]) == int(source["totalFrames"]), "FER denominator mismatch")
            if r["isZeroObserved"] == "true":
                req(r["plotSurrogateUsed"] == "true", "zero surrogate flag mismatch")
                req(close(r["plotY"], 0.5 / int(r["rawDenominator"])), "zero surrogate value mismatch")
            else:
                req(r["plotSurrogateUsed"] == "false" and close(r["plotY"], r["rawY"]),
                    "non-zero plotY mismatch")


def write_summaries(data):
    reasons = Counter(r["stopReason"] for r in data)
    total_frames = sum(int(r["totalFrames"]) for r in data)
    zero_ber = sum(1 for r in data if float(r["ber"]) == 0.0)
    zero_fer = sum(1 for r in data if float(r["fer"]) == 0.0)
    summary = [
        {"metric": "formalPoints", "value": 296},
        {"metric": "totalFrames", "value": total_frames},
        {"metric": "targetStops", "value": reasons["TARGET_FRAME_ERRORS_REACHED"]},
        {"metric": "maxStops", "value": reasons["MAX_FRAMES_REACHED"]},
        {"metric": "zeroBerPoints", "value": zero_ber},
        {"metric": "zeroFerPoints", "value": zero_fer},
        {"metric": "plots", "value": 6},
    ]
    write_csv(RESULTS / "stage07_awgn_dense_formal_summary.csv", summary, ["metric", "value"])
    stop_rows = [{"stopReason": k, "points": v} for k, v in sorted(reasons.items())]
    write_csv(RESULTS / "stage07_awgn_dense_formal_stop_reason_summary.csv", stop_rows,
              ["stopReason", "points"])
    audit = []
    for r in data:
        audit.append({
            "caseId": r["caseId"], "snrIndex": r["snrIndex"], "snrDb": r["snrDb"],
            "totalFrames": r["totalFrames"], "payloadErrorFrames": r["payloadErrorFrames"],
            "stopReason": r["stopReason"], "ber": r["ber"], "fer": r["fer"], "passed": "true",
        })
    write_csv(RESULTS / "stage07_awgn_dense_formal_point_audit.csv", audit)
    manifest = {
        "stageId": "stage07_awgn_dense_formal",
        "results": "stage07_awgn_dense_formal_results.csv",
        "resultsSha256": sha(RESULTS / "stage07_awgn_dense_formal_results.csv"),
        "progress": "stage07_awgn_dense_formal_progress.csv",
        "progressSha256": sha(RESULTS / "stage07_awgn_dense_formal_progress.csv"),
        "points": "stage07_awgn_dense_formal_points.csv",
        "pointsSha256": sha(RESULTS / "stage07_awgn_dense_formal_points.csv"),
        "formalPoints": 296,
        "totalFrames": total_frames,
    }
    (RESULTS / "stage07_awgn_dense_formal_raw_results_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_stage06_compare(data):
    if not STAGE06.exists():
        write_csv(RESULTS / "stage07_awgn_dense_formal_stage06_overlap_compare.csv",
                  [{"caseId": "ALL", "statisticalComment": "NO_STAGE06_RESULTS"}],
                  ["caseId", "statisticalComment"])
        return
    old = rows(STAGE06)
    by_key = {(r["caseId"], round(float(r["snrDb"]), 10)): r for r in data}
    compare = []
    for s6 in old:
        key = (s6["caseId"], round(float(s6["snrDb"]), 10))
        if key not in by_key:
            continue
        s7 = by_key[key]
        diff = abs(float(s7["fer"]) - float(s6["fer"]))
        rel = diff / max(float(s6["fer"]), 1e-300)
        compare.append({
            "caseId": s6["caseId"],
            "stage06SnrDb": s6["snrDb"],
            "stage07SnrDb": s7["snrDb"],
            "stage06Ber": s6["ber"],
            "stage07Ber": s7["ber"],
            "stage06Fer": s6["fer"],
            "stage07Fer": s7["fer"],
            "stage06Frames": s6["totalFrames"],
            "stage07Frames": s7["totalFrames"],
            "absoluteDifference": f"{diff:.17g}",
            "relativeDifference": f"{rel:.17g}",
            "statisticalComment": "EXACT_WAVEFORM_SNR_OVERLAP_DIFFERENT_STAGEID_STREAMS",
        })
    if not compare:
        compare = [{
            "caseId": "ALL", "stage06SnrDb": "", "stage07SnrDb": "", "stage06Ber": "",
            "stage07Ber": "", "stage06Fer": "", "stage07Fer": "", "stage06Frames": "",
            "stage07Frames": "", "absoluteDifference": "", "relativeDifference": "",
            "statisticalComment": "NO_EXACT_OVERLAP",
        }]
    write_csv(RESULTS / "stage07_awgn_dense_formal_stage06_overlap_compare.csv", compare)


def main():
    data = rows(RESULTS / "stage07_awgn_dense_formal_results.csv")
    check_config_and_results(data)
    check_points_and_progress(data)
    check_figures(data)
    req("100% tests passed" in (LOGS / "stage07_awgn_dense_formal_ctest.log").read_text(encoding="utf-8"),
        "CTest did not pass")
    req("PASS_STAGE07_RESUME_EQUIVALENCE" in
        (LOGS / "stage07_awgn_dense_formal_resume_test.log").read_text(encoding="utf-8"),
        "resume equivalence did not pass")
    req("PASS_STAGE07_AWGN_DENSE_FORMAL_RUNNER" in
        (LOGS / "stage07_awgn_dense_formal_runner.log").read_text(encoding="utf-8"),
        "runner did not pass")
    req("PASS_STAGE07_AWGN_DENSE_FORMAL_PLOT" in
        (LOGS / "stage07_awgn_dense_formal_plot.log").read_text(encoding="utf-8"),
        "plot did not pass")
    write_summaries(data)
    write_stage06_compare(data)
    for src in (
        RESULTS / "stage07_awgn_dense_formal_results.csv",
        RESULTS / "stage07_awgn_dense_formal_summary.csv",
        RESULTS / "stage07_awgn_dense_formal_stop_reason_summary.csv",
        RESULTS / "stage07_awgn_dense_formal_point_audit.csv",
        RESULTS / "stage07_awgn_dense_formal_raw_results_manifest.json",
    ):
        dst = PUBLISHED / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
    print("PASS_STAGE07_AWGN_DENSE_PLOT_CHECK")
    print("PASS_STAGE07_AWGN_DENSE_FORMAL")
    print("PASS_BCH_S2_AWGN_DENSE_RERUN")


if __name__ == "__main__":
    main()
