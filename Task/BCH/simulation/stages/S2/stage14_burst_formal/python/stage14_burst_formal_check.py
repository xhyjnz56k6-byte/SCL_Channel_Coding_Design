import argparse
import csv
import hashlib
import json
import math
import platform
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
STAGE = Path(__file__).resolve().parents[1]
STAGE13 = STAGE.parent / "stage13_burst_interleaving_validation"
RESULTS = STAGE / "results"
LOGS = RESULTS / "logs"
STAGE_ID = "stage14_burst_formal"
GATE = "PASS_STAGE14_BURST_FORMAL"
BASE_COMMIT = "6770561e04a7f0c8527314568cdffde30603f030"
CASES = {
    "K200_S15": (200, 285),
    "K200_M255K207": (200, 248),
    "K200_M511K421": (200, 290),
    "K200_M511K385": (200, 326),
    "K300_S15": (300, 420),
    "K300_M255K207": (300, 396),
    "K300_M511K421": (300, 390),
    "K300_M511K385": (300, 426),
}


def require(condition, message):
    if not condition:
        raise SystemExit("BLOCKED_STAGE14_BURST_FORMAL_CHECK: " + message)


def read_rows(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*arguments):
    return subprocess.check_output(
        ["git", *arguments], cwd=ROOT, text=True
    ).strip()


def close(left, right):
    return math.isclose(
        float(left), float(right), rel_tol=1e-11, abs_tol=1e-14
    )


def canonical_row_sha(row, fields):
    text = ",".join(
        row[field] for field in fields if field != "resultSha256"
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def check_raw(config, frozen):
    path = RESULTS / f"{STAGE_ID}_raw_results.csv"
    rows = read_rows(path)
    expected = {
        (
            case_id,
            length,
        )
        for case_id, (payload, _) in CASES.items()
        for length in frozen["stage14BurstLengthsByPayload"][str(payload)]
    }
    observed = {
        (row["caseId"], int(row["burstLengthBits"])) for row in rows
    }
    require(len(rows) == 128 and observed == expected, "formal grid differs")
    require(len(observed) == len(rows), "duplicate formal point")
    fields = list(rows[0])
    stop = config["stopRule"]
    for row in rows:
        case_id = row["caseId"]
        payload, encoded = CASES[case_id]
        frames = int(row["framesProcessed"])
        payload_bits = int(row["payloadBitsProcessed"])
        error_bits = int(row["payloadErrorBits"])
        error_frames = int(row["payloadErrorFrames"])
        declared_success = int(row["decoderDeclaredSuccessFrames"])
        declared_failure = int(row["decoderDeclaredFailureFrames"])
        true_success = int(row["trueSuccessFrames"])
        miscorrection = int(row["miscorrectionFrames"])
        undetected = int(row["undetectedErrorFrames"])
        affected_total = int(row["affectedCodeBlocksTotal"])
        sum_max_errors = round(
            float(row["meanMaxErrorsInOneCodeBlock"]) * frames
        )
        require(
            row["stageId"] == STAGE_ID
            and row["burstStartPolicy"] == "RANDOM_PER_FRAME"
            and row["burstWrapAround"].lower() == "false",
            "channel contract mismatch",
        )
        require(
            int(row["payloadLength"]) == payload
            and int(row["encodedLength"]) == encoded
            and close(row["actualRate"], payload / encoded),
            "case length/rate mismatch",
        )
        require(
            stop["minFrames"] <= frames <= stop["maxFrames"],
            "frame count outside formal rule",
        )
        if row["stopReason"] == "TARGET_FRAME_ERRORS_REACHED":
            require(
                error_frames >= stop["targetFrameErrors"],
                "target stop before target",
            )
        elif row["stopReason"] == "MAX_FRAMES_REACHED":
            require(
                frames == stop["maxFrames"]
                and error_frames < stop["targetFrameErrors"],
                "max stop invalid",
            )
        else:
            require(False, "unknown formal stopReason")
        require(payload_bits == payload * frames, "payload denominator differs")
        require(
            declared_success + declared_failure == frames,
            "decoder status accounting differs",
        )
        require(
            true_success + error_frames == frames,
            "true-success accounting differs",
        )
        require(
            miscorrection <= declared_success
            and undetected <= miscorrection,
            "miscorrection/undetected accounting differs",
        )
        require(
            close(row["ber"], error_bits / payload_bits)
            and close(row["fer"], error_frames / frames)
            and close(row["decoderFailureRate"], declared_failure / frames)
            and close(row["miscorrectionRate"], miscorrection / frames)
            and close(row["undetectedErrorRate"], undetected / frames)
            and close(row["trueSuccessRate"], true_success / frames),
            "derived rate mismatch",
        )
        require(
            close(row["meanAffectedCodeBlocks"], affected_total / frames),
            "affected-block mean mismatch",
        )
        require(
            all(
                math.isfinite(float(row[field]))
                for field in (
                    "ber", "fer", "decoderFailureRate",
                    "miscorrectionRate", "undetectedErrorRate",
                    "decoderTimeMeanNs", "decoderTimeP99Ns",
                )
            ),
            "formal row contains NaN/Inf",
        )
        require(
            row["resultSha256"] == canonical_row_sha(row, fields),
            "row resultSha256 mismatch",
        )
        checkpoint = STAGE / row["checkpointPath"]
        require(checkpoint.is_file(), "checkpoint missing")
        checkpoint_data = json.loads(checkpoint.read_text(encoding="utf-8"))
        require(
            checkpoint_data["caseId"] == case_id
            and checkpoint_data["framesProcessed"] == frames
            and checkpoint_data["payloadErrorFrames"] == error_frames
            and checkpoint_data["gitCommit"] == row["gitCommit"]
            and checkpoint_data["stopReason"] == row["stopReason"],
            "checkpoint content differs from result",
        )
        if int(row["burstLengthBits"]) == 0:
            require(
                affected_total == 0
                and int(row["maxAffectedCodeBlocks"]) == 0
                and int(row["maxErrorsInOneCodeBlockObserved"]) == 0,
                "L=0 affected-block statistics nonzero",
            )
        require(
            int(row["decoderTimeP50Ns"])
            <= int(row["decoderTimeP95Ns"])
            <= int(row["decoderTimeP99Ns"])
            <= int(row["decoderTimeMaxNs"]),
            "latency percentiles not monotonic",
        )
    commits = {row["gitCommit"] for row in rows}
    require(len(commits) == 1, "formal rows reference multiple commits")
    return rows


def check_derived(rows):
    expected_counts = {
        f"{STAGE_ID}_summary.csv": 128,
        f"{STAGE_ID}_decoder_status.csv": 128,
        f"{STAGE_ID}_affected_blocks.csv": 128,
        f"{STAGE_ID}_latency.csv": 128,
        f"{STAGE_ID}_tolerance.csv": 8,
        f"{STAGE_ID}_shard_manifest.csv": 128,
        f"{STAGE_ID}_merge_audit.csv": 4,
    }
    for name, count in expected_counts.items():
        require(
            len(read_rows(RESULTS / name)) == count,
            f"{name} row count differs",
        )
    merge = read_rows(RESULTS / f"{STAGE_ID}_merge_audit.csv")
    require(
        all(row["passed"].lower() in {"1", "true"} for row in merge),
        "shard merge audit failed",
    )
    require(
        len(list((RESULTS / "checkpoints").glob("*.json"))) == 128,
        "checkpoint count is not 128",
    )


def check_matlab():
    samples = read_rows(RESULTS / f"{STAGE_ID}_matlab_samples.csv")
    comparison = read_rows(
        RESULTS / f"{STAGE_ID}_matlab_comparison.csv"
    )
    require(len(samples) == len(comparison) == 24, "MATLAB sample count differs")
    for row in comparison:
        require(
            row["passed"].lower() in {"1", "true"}
            and int(float(row["burstPositionMismatch"])) == 0
            and int(float(row["decodedPayloadMismatch"])) == 0
            and int(float(row["statusMismatch"])) == 0,
            "MATLAB comparison mismatch",
        )


def check_plots(rows):
    png_files = sorted((RESULTS / "plots").glob("*.png"))
    data_files = sorted((RESULTS / "figure_data").glob("*.csv"))
    manifests = sorted((RESULTS / "manifests").glob("*_plot_manifest.json"))
    require(
        len(png_files) == len(data_files) == len(manifests) == 13,
        "plot/data/manifest count is not 13",
    )
    source_sha = sha256(RESULTS / f"{STAGE_ID}_raw_results.csv")
    total_points = 0
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        png = STAGE / manifest["pngFile"]
        data = STAGE / manifest["figureDataFile"]
        require(
            png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n",
            "plot is not PNG",
        )
        require(
            sha256(png) == manifest["pngSha256"]
            and sha256(data) == manifest["figureDataSha256"]
            and manifest["sourceSha256"] == [source_sha],
            "plot hash mismatch",
        )
        figure_rows = read_rows(data)
        total_points += len(figure_rows)
        require(
            len(manifest["legendLabels"])
            == len(set(row["caseId"] for row in figure_rows)),
            "legend count differs from curve count",
        )
        require(
            all(row["legendLabel"] not in CASES for row in figure_rows),
            "internal case ID used as legend",
        )
        for row in figure_rows:
            require(
                all(
                    math.isfinite(float(row[field]))
                    for field in ("xRaw", "xDisplay", "yRaw", "yPlot")
                ),
                "figure-data contains NaN/Inf",
            )
            if row["ferIsZero"] == "true":
                require(
                    float(row["ferRaw"]) == 0.0
                    and close(
                        row["ferPlot"],
                        0.5 / int(row["framesProcessed"]),
                    ),
                    "FER zero surrogate mismatch",
                )
            if row["berIsZero"] == "true":
                require(
                    float(row["berRaw"]) == 0.0
                    and close(
                        row["berPlot"],
                        0.5 / int(row["payloadBitsProcessed"]),
                    ),
                    "BER zero surrogate mismatch",
                )
    require(total_points == 1024, "figure-data total point count differs")
    forbidden = [
        path for path in RESULTS.rglob("*")
        if path.suffix.lower() in {".pdf", ".svg", ".eps", ".jpg", ".jpeg"}
    ]
    require(not forbidden, "forbidden plot format exists")


def check_logs():
    require(
        "100% tests passed"
        in (LOGS / f"{STAGE_ID}_ctest.log").read_text(encoding="utf-8"),
        "CTest log is not PASS",
    )
    for shard_id in range(4):
        require(
            "PASS_STAGE14_BURST_FORMAL_RUNNER"
            in (LOGS / f"{STAGE_ID}_shard_{shard_id}.log").read_text(
                encoding="utf-8"
            ),
            f"shard {shard_id} runner token missing",
        )
    require(
        "PASS_STAGE14_BURST_FORMAL_FINALIZE"
        in (LOGS / f"{STAGE_ID}_finalize.log").read_text(encoding="utf-8"),
        "finalize token missing",
    )
    require(
        "PASS_STAGE14_BURST_FORMAL_MATLAB_REFERENCE"
        in (LOGS / f"{STAGE_ID}_matlab.log").read_text(encoding="utf-8"),
        "MATLAB token missing",
    )
    require(
        "PASS_STAGE14_BURST_FORMAL_PLOT"
        in (LOGS / f"{STAGE_ID}_plot.log").read_text(encoding="utf-8"),
        "plot token missing",
    )


def write_audit(rows, config, code_commit, result_commit):
    reasons = Counter(row["stopReason"] for row in rows)
    total_frames = sum(int(row["framesProcessed"]) for row in rows)
    summary = [
        ("formalPoints", len(rows)),
        ("totalFrames", total_frames),
        ("targetStops", reasons["TARGET_FRAME_ERRORS_REACHED"]),
        ("maxStops", reasons["MAX_FRAMES_REACHED"]),
        ("csvFiles", len(list(RESULTS.rglob("*.csv")))),
        ("pngFiles", len(list(RESULTS.rglob("*.png")))),
        ("figureDataFiles", len(list((RESULTS / "figure_data").glob("*.csv")))),
        ("plotManifests", len(list((RESULTS / "manifests").glob("*.json")))),
    ]
    with (
        RESULTS / f"{STAGE_ID}_result_summary.csv"
    ).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["metric", "value"])
        writer.writerows(summary)

    excluded = {
        f"{STAGE_ID}_sha256.csv",
        f"{STAGE_ID}_manifest.json",
        f"{STAGE_ID}_gate.txt",
        f"{STAGE_ID}_report.md",
    }
    evidence = sorted(
        path for path in RESULTS.rglob("*")
        if path.is_file() and path.name not in excluded
    )
    with (
        RESULTS / f"{STAGE_ID}_sha256.csv"
    ).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["file", "sha256"])
        for path in evidence:
            writer.writerow([path.relative_to(STAGE).as_posix(), sha256(path)])

    ranges = []
    if code_commit:
        ranges.append({
            "name": "implementation",
            "baseCommit": BASE_COMMIT,
            "contentCommit": code_commit,
            "files": git(
                "diff", "--name-only", f"{BASE_COMMIT}...{code_commit}"
            ).splitlines(),
        })
    if result_commit:
        ranges.append({
            "name": "formalResults",
            "baseCommit": code_commit,
            "contentCommit": result_commit,
            "files": git(
                "diff", "--name-only", f"{code_commit}...{result_commit}"
            ).splitlines(),
        })
    final = bool(code_commit and result_commit)
    gate = GATE if final else f"{GATE}_FUNCTIONAL"
    manifest = {
        "stage": STAGE_ID,
        "branch": git("branch", "--show-current"),
        "functionalRanges": ranges,
        "codeCommit": code_commit or "WORKTREE",
        "resultCommit": result_commit or "WORKTREE",
        "formalPointCount": 128,
        "totalFrames": total_frames,
        "stopReasonCounts": dict(reasons),
        "configFile": f"configs/{STAGE_ID}_config.json",
        "resultFile": f"results/{STAGE_ID}_raw_results.csv",
        "resultSha256": sha256(RESULTS / f"{STAGE_ID}_raw_results.csv"),
        "checkerVersion": "stage14-checker-v1",
        "runnerVersion": "stage14-runner-v1",
        "compiler": "GNU MinGW",
        "buildType": "Release",
        "os": platform.platform(),
        "pythonVersion": platform.python_version(),
        "matlabVersion": "captured-in-matlab-log",
        "gate": gate,
        "remoteVerification": "DEFERRED_TO_AUTHORIZED_BATCH_PUSH",
        "mergeStatus": "NOT_MERGED",
    }
    (RESULTS / f"{STAGE_ID}_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (RESULTS / f"{STAGE_ID}_gate.txt").write_text(
        gate + "\n", encoding="utf-8"
    )
    report = f"""# Stage14 无交织连续突发错误正式实验报告

- 分支：`{manifest['branch']}`
- 代码提交：`{code_commit or '功能工作树'}`
- 结果提交：`{result_commit or '结果工作树'}`
- 正式点：128
- 累计帧数：{total_frames}
- TARGET_FRAME_ERRORS_REACHED：{reasons['TARGET_FRAME_ERRORS_REACHED']} 点
- MAX_FRAMES_REACHED：{reasons['MAX_FRAMES_REACHED']} 点
- MATLAB 抽查：24/24，位置、payload、status mismatch 均为 0
- checkpoint：128 个
- PNG/figure-data/plot manifest：13/13/13
- Gate：`{gate}`

突发容限和不同 Case 的相对表现保存在 canonical tolerance/summary CSV；
本报告不预设任何 Case 排名。
"""
    (RESULTS / f"{STAGE_ID}_report.md").write_text(
        report, encoding="utf-8"
    )
    validation = f"""# Stage14 Validation Report

- Debug/Release build: PASS
- CTest: PASS
- Smoke: PASS
- Formal runner shards: PASS (4/4)
- Formal point checker: PASS (128/128)
- MATLAB comparison: PASS (24/24)
- Plot publication checker: PASS (13/13)
- Checkpoint and merge audit: PASS
- Gate: {gate}
- Merge status: NOT_MERGED
"""
    (STAGE / f"{STAGE_ID}_validation_report.md").write_text(
        validation, encoding="utf-8"
    )
    (STAGE / f"{STAGE_ID}_known_issues.md").write_text(
        """# Stage14 Known Issues

- 本阶段只评价无交织连续突发错误；交织收益在 Stage15 评价。
- 远程包含性将在批次最终 push 后统一验证。
- 未使用插值扩充任何原始突发长度点。
""",
        encoding="utf-8",
    )
    (STAGE / f"{STAGE_ID}_commands_used.md").write_text(
        """# Stage14 Commands Used

```powershell
python stage14_burst_formal_run.py
git commit -m "BCH/Stage14：实现无交织突发正式实验"
python stage14_burst_formal_run.py --formal
python stage14_burst_formal_check.py
```

正式运行使用 4 个点级 shard；每个点仍按 frameIndex 0 开始并独立停止。
""",
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-commit")
    parser.add_argument("--result-commit")
    args = parser.parse_args()
    require(
        not args.result_commit or args.code_commit,
        "result commit requires code commit",
    )
    config = json.loads(
        (STAGE / f"configs/{STAGE_ID}_config.json").read_text(
            encoding="utf-8"
        )
    )
    frozen = json.loads(
        (
            STAGE13
            / "results/stage13_burst_interleaving_validation_frozen_parameters.json"
        ).read_text(encoding="utf-8")
    )
    require(
        config["stopRule"] == frozen["formalStopRule"],
        "Stage14 stop rule differs from Stage13 freeze",
    )
    rows = check_raw(config, frozen)
    check_derived(rows)
    check_matlab()
    check_plots(rows)
    check_logs()
    write_audit(rows, config, args.code_commit, args.result_commit)
    print(
        GATE if args.code_commit and args.result_commit
        else f"{GATE}_FUNCTIONAL"
    )


if __name__ == "__main__":
    main()

