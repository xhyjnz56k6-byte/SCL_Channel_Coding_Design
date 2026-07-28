import csv
import json
import math
from pathlib import Path


STAGE = Path(__file__).resolve().parents[1]
RESULTS = STAGE / "results"
LOGS = STAGE / "logs"
PLOTS = STAGE / "plots"
CASES = {
    "K200_S15", "K200_M255K207", "K200_M511K421", "K200_M511K385",
    "K300_S15", "K300_M255K207", "K300_M511K421", "K300_M511K385",
}


def rows(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def require(value, message):
    if not value:
        raise SystemExit(f"BLOCKED_STAGE05_AWGN_TRIAL_CHECK: {message}")


def close(a, b, tolerance=1e-11):
    return math.isclose(float(a), float(b), rel_tol=tolerance, abs_tol=tolerance)


def main():
    config = json.loads((STAGE / "configs" / "stage05_awgn_trial_config.json").read_text(encoding="utf-8"))
    require(config["stageId"] == "stage05_awgn_trial", "stage ID mismatch")
    require(set(config["points"]) == CASES, "point grid case set mismatch")
    require(all(len(points) == 3 for points in config["points"].values()), "not exactly 3 points per case")
    require(config["framesPerPoint"] == 500, "trial frame count mismatch")
    require(config["formalStopRuleToValidate"] ==
            {"minFrames": 5000, "targetFrameErrors": 200, "maxFrames": 50000},
            "formal stop rule is not frozen")
    require(not any("prescan" in path.name.lower() for path in STAGE.rglob("*")),
            "a prescan-named artifact exists")

    result_rows = rows(RESULTS / "stage05_awgn_trial_results.csv")
    require(len(result_rows) == 24, "result row count is not 24")
    require(set(row["caseId"] for row in result_rows) == CASES, "result case set mismatch")
    require(all(int(row["totalFrames"]) == 500 for row in result_rows), "point is not 500 frames")
    require(all(row["stopReason"] == "SMOKE_FIXED_FRAMES" for row in result_rows),
            "trial stop reason mismatch")
    require(len({(row["caseId"], row["ebn0Index"]) for row in result_rows}) == 24,
            "duplicate case/point identity")
    for row in result_rows:
        frames = int(row["totalFrames"])
        bits = int(row["totalPayloadBits"])
        bit_errors = int(row["payloadErrorBits"])
        frame_errors = int(row["payloadErrorFrames"])
        require(int(row["trueSuccessFrames"]) + frame_errors == frames, "frame accounting mismatch")
        require(0 <= int(row["decoderFailureFrames"]) <= frames, "decoder failure count invalid")
        require(0 <= int(row["miscorrectionFrames"]) <= frames, "miscorrection count invalid")
        require(0 <= int(row["undetectedErrorFrames"]) <= frames, "undetected count invalid")
        require(close(row["ber"], bit_errors / bits), "BER does not match raw counts")
        require(close(row["fer"], frame_errors / frames), "FER does not match raw counts")
        rate = float(row["actualRate"])
        ebn0 = float(row["ebn0Db"])
        sigma2 = 1.0 / (2.0 * rate * 10.0 ** (ebn0 / 10.0))
        snr_db = ebn0 + 10.0 * math.log10(2.0 * rate)
        require(close(row["sigma2"], sigma2), "sigma2 formula mismatch")
        require(close(row["snrDb"], snr_db), "SNR dB formula mismatch")
        require(close(row["snrLinear"], 1.0 / sigma2), "SNR linear formula mismatch")
        numeric = [float(row[name]) for name in
                   ("ber", "fer", "sigma2", "snrLinear", "snrDb", "encodeTimeMeanNs",
                    "decodeTimeMeanNs", "decodeTimeP50Ns", "decodeTimeP95Ns",
                    "decodeTimeP99Ns", "decodeTimeMaxNs")]
        require(all(math.isfinite(value) for value in numeric), "NaN or Inf in results")

    resume = rows(RESULTS / "stage05_awgn_trial_resume_compare.csv")
    shard = rows(RESULTS / "stage05_awgn_trial_shard_merge_compare.csv")
    require(len(resume) == 8 and all(row["passed"] in ("1", "true") for row in resume),
            "resume equivalence is not 8/8")
    require(len(shard) == 8 and all(row["passed"] in ("1", "true") for row in shard),
            "shard equivalence is not 8/8")
    require(all(row["allIntegerCountsEqual"] in ("1", "true") for row in resume + shard),
            "raw integer counts differ")
    require(len(rows(RESULTS / "stage05_awgn_trial_shard_manifest.csv")) == 24,
            "shard manifest row count mismatch")
    checkpoints = list((RESULTS / "checkpoints").glob("*.json"))
    require(len(checkpoints) == 8, "checkpoint count is not 8")
    for path in checkpoints:
        checkpoint = json.loads(path.read_text(encoding="utf-8"))
        require(checkpoint["stageId"] == "stage05_awgn_trial" and
                checkpoint["nextFrameIndex"] == 211 and checkpoint["totalFrames"] == 211,
                f"invalid checkpoint {path.name}")

    stop_rows = rows(RESULTS / "stage05_awgn_trial_formal_stop_rule_test.csv")
    expected = ["CONTINUE", "TARGET_FRAME_ERRORS_REACHED", "CONTINUE", "MAX_FRAMES_REACHED"]
    require([row["decision"] for row in stop_rows] == expected, "formal stop rule test mismatch")
    require(len(rows(RESULTS / "stage05_awgn_trial_runtime_estimate.csv")) == 24,
            "runtime estimate row count mismatch")

    manifest = json.loads((PLOTS / "stage05_awgn_trial_plot_manifest.json").read_text(encoding="utf-8"))
    require(manifest["stageId"] == "stage05_awgn_trial", "plot manifest stage mismatch")
    require(len(manifest["figures"]) == 4, "plot count is not 4")
    aggregate = rows(PLOTS / "stage05_awgn_trial_figure_data.csv")
    require(len(aggregate) == 48, "aggregate figure data row count mismatch")
    for figure in manifest["figures"]:
        png = PLOTS / figure["png"]
        data = PLOTS / figure["figureData"]
        require(png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", f"{png.name} is not PNG")
        require(figure["dpi"] == 300 and figure["xAxis"] == "SNR (dB)", "plot contract mismatch")
        require(len(rows(data)) == 12, f"{data.name} row count mismatch")
    forbidden = {".pdf", ".svg", ".eps", ".jpg", ".jpeg"}
    require(not any(path.suffix.lower() in forbidden for path in PLOTS.iterdir()),
            "forbidden plot format exists")
    ctest = (LOGS / "stage05_awgn_trial_ctest.log").read_text(encoding="utf-8")
    runner = (LOGS / "stage05_awgn_trial_runner.log").read_text(encoding="utf-8")
    plot_log = (LOGS / "stage05_awgn_trial_plot.log").read_text(encoding="utf-8")
    require("100% tests passed" in ctest, "CTest failed")
    require("PASS_STAGE05_AWGN_TRIAL_RUNNER" in runner, "runner Gate failed")
    require("PASS_STAGE05_AWGN_TRIAL_PLOT" in plot_log, "plot Gate failed")
    (STAGE / "stage05_awgn_trial_test_summary.csv").write_text(
        "test,executed,result,detail\n"
        "fixed trial grid,true,PASS,8 cases x 3 points x 500 frames\n"
        "AWGN formulas and raw counters,true,PASS,24/24\n"
        "checkpoint resume,true,PASS,8/8 exact\n"
        "three-shard merge,true,PASS,8/8 exact\n"
        "formal stop rule,true,PASS,4 boundary decisions\n"
        "PNG plot contract,true,PASS,4/4 at 300 dpi\n",
        encoding="utf-8")
    print("PASS_STAGE05_AWGN_TRIAL")


if __name__ == "__main__":
    main()
