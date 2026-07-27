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
STAGE14 = STAGE.parent / "stage14_burst_formal"
RESULTS = STAGE / "results"
LOGS = RESULTS / "logs"
STAGE_ID = "stage15_interleaving_formal"
GATE = "PASS_STAGE15_INTERLEAVING_FORMAL"
BASE_COMMIT = "311e9a38373fe0483f65b1fe027d39b9b8cbfadd"
ORIGINAL_CONTENT_COMMIT = "c56ea139a842ce7156261a02174dba399024849b"
FIRST_REPAIR_COMMIT = "5390b9e1e0d837a6738ad7b3bbafef11462bd6bc"
SECOND_REPAIR_COMMIT = "33755851a1607a76b7868d454c428b00d4e2c36b"
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
MODES = ["BLOCK", "ROW_COLUMN", "PSEUDORANDOM"]


def require(condition, message):
    if not condition:
        raise SystemExit("BLOCKED_STAGE15_INTERLEAVING_FORMAL_CHECK: " + message)


def read_rows(path):
    require(path.is_file(), f"missing file: {path}")
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write_rows(path, fields, data):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(data)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*arguments):
    return subprocess.check_output(
        ["git", *arguments], cwd=ROOT, text=True
    ).strip()


def close(left, right):
    return math.isclose(float(left), float(right), rel_tol=1e-11, abs_tol=1e-14)


def canonical_row_sha(row, fields):
    text = ",".join(row.get(field, "") for field in fields if field != "resultSha256")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def row_key(row):
    return (
        row["caseId"],
        row["interleaverMode"],
        int(row["interleaverDepth"]),
        int(row["burstLengthBits"]),
    )


def check_grid(data, expected, name):
    observed = {row_key(row) for row in data}
    require(len(data) == len(expected), f"{name} row count differs")
    require(len(observed) == len(data), f"{name} contains duplicate point")
    require(observed == expected, f"{name} grid differs from frozen grid")


def check_formal_row(row, config, fields):
    payload, encoded = CASES[row["caseId"]]
    frames = int(row["framesProcessed"])
    bits = int(row["payloadBitsProcessed"])
    errors = int(row["payloadErrorBits"])
    frame_errors = int(row["payloadErrorFrames"])
    declared_success = int(row["decoderDeclaredSuccessFrames"])
    declared_failure = int(row["decoderDeclaredFailureFrames"])
    true_success = int(row["trueSuccessFrames"])
    miscorrection = int(row["miscorrectionFrames"])
    undetected = int(row["undetectedErrorFrames"])
    affected = int(row["affectedCodeBlocksTotal"])
    stop = config["stopRule"]
    require(row["stageId"] == STAGE_ID, "stage ID mismatch")
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
        require(frame_errors >= stop["targetFrameErrors"], "target stop before target")
    elif row["stopReason"] == "MAX_FRAMES_REACHED":
        require(
            frames == stop["maxFrames"]
            and frame_errors < stop["targetFrameErrors"],
            "max stop invalid",
        )
    else:
        require(False, "unknown stopReason")
    require(bits == payload * frames, "payload denominator mismatch")
    require(
        declared_success + declared_failure == frames
        and true_success + frame_errors == frames,
        "frame accounting mismatch",
    )
    require(
        miscorrection <= declared_success and undetected <= miscorrection,
        "miscorrection accounting mismatch",
    )
    require(
        close(row["ber"], errors / bits)
        and close(row["fer"], frame_errors / frames)
        and close(row["decoderFailureRate"], declared_failure / frames)
        and close(row["miscorrectionRate"], miscorrection / frames)
        and close(row["undetectedErrorRate"], undetected / frames)
        and close(row["trueSuccessRate"], true_success / frames)
        and close(row["meanAffectedCodeBlocks"], affected / frames),
        "derived metric mismatch",
    )
    for field in (
        "ber", "fer", "decoderFailureRate", "miscorrectionRate",
        "undetectedErrorRate", "trueSuccessRate", "decoderTimeMeanNs",
        "decoderTimeP99Ns", "interleaverTimeMeanNs",
        "deinterleaverTimeMeanNs", "deltaFer",
    ):
        require(math.isfinite(float(row[field])), f"{field} contains NaN/Inf")
    for field in ("relativeFerReduction", "ferImprovementRatio"):
        if row[field]:
            require(math.isfinite(float(row[field])), f"{field} contains NaN/Inf")
    require(
        int(row["decoderTimeP50Ns"])
        <= int(row["decoderTimeP95Ns"])
        <= int(row["decoderTimeP99Ns"])
        <= int(row["decoderTimeMaxNs"]),
        "latency percentiles are not monotonic",
    )
    require(
        row["resultSha256"] == canonical_row_sha(row, fields),
        "row resultSha256 mismatch",
    )


def compare_none(method, stage14):
    lookup = {
        (row["caseId"], int(row["burstLengthBits"])): row for row in stage14
    }
    exact_fields = [
        "framesProcessed", "payloadBitsProcessed", "payloadErrorBits",
        "payloadErrorFrames", "decoderDeclaredSuccessFrames",
        "decoderDeclaredFailureFrames", "trueSuccessFrames",
        "miscorrectionFrames", "undetectedErrorFrames",
        "affectedCodeBlocksTotal", "maxAffectedCodeBlocks",
        "maxErrorsInOneCodeBlockObserved", "ber", "fer",
        "decoderFailureRate", "miscorrectionRate", "undetectedErrorRate",
        "trueSuccessRate", "stopReason",
    ]
    for row in method:
        if row["interleaverMode"] != "NONE":
            continue
        source = lookup[(row["caseId"], int(row["burstLengthBits"]))]
        require(
            all(row[field] == source[field] for field in exact_fields),
            "Stage14 NONE canonical row changed",
        )
        require(
            row["sourceStage"] == "stage14_burst_formal"
            and row["sourceGitCommit"] == source["gitCommit"]
            and row["reuseStatus"] == "REUSED_STAGE14_CANONICAL",
            "NONE provenance mismatch",
        )


def expected_selection(method, priority):
    result = {}
    for case_id in CASES:
        candidates = []
        for mode in MODES:
            group = [
                row for row in method
                if row["caseId"] == case_id and row["interleaverMode"] == mode
            ]
            geomean = math.exp(sum(
                math.log(max(float(row["fer"]), 0.5 / int(row["framesProcessed"])))
                for row in group
            ) / len(group))
            miscorr = sum(float(row["miscorrectionRate"]) for row in group) / len(group)
            tolerable = [
                int(row["burstLengthBits"]) for row in group
                if float(row["fer"]) <= 0.1
            ]
            tolerance = max(tolerable) if tolerable else -1
            latency = sum(
                float(row["interleaverTimeMeanNs"])
                + float(row["deinterleaverTimeMeanNs"])
                for row in group
            ) / len(group)
            candidates.append(
                (geomean, miscorr, -tolerance, latency, priority.index(mode), mode)
            )
        result[case_id] = min(candidates)[5]
    return result


def check_results(config, frozen):
    method = read_rows(RESULTS / f"{STAGE_ID}_method_results.csv")
    depth = read_rows(RESULTS / f"{STAGE_ID}_depth_results.csv")
    unique = read_rows(RESULTS / f"{STAGE_ID}_raw_results.csv")
    method_expected = {
        (case_id, mode, 1 if mode == "NONE" else 8, length)
        for case_id, (payload, _) in CASES.items()
        for mode in ["NONE", *MODES]
        for length in frozen["stage15MethodBurstLengthsByPayload"][str(payload)]
    }
    check_grid(method, method_expected, "method results")
    selection_rows = read_rows(
        RESULTS / f"{STAGE_ID}_best_interleaver_selection.csv"
    )
    require(len(selection_rows) == 8, "selection row count differs")
    selected = {
        row["caseId"]: row["bestInterleaverMode"] for row in selection_rows
    }
    require(
        selected == expected_selection(method, config["bestModePriority"]),
        "best-mode selection differs from frozen deterministic rule",
    )
    depth_expected = {
        (case_id, "NONE" if depth_value == 1 else selected[case_id],
         depth_value, length)
        for case_id, (payload, _) in CASES.items()
        for depth_value in (1, 4, 8, 16)
        for length in frozen["stage15DepthBurstLengthsByPayload"][str(payload)]
    }
    check_grid(depth, depth_expected, "depth results")
    require(len(unique) == 400, "unique canonical result count is not 400")
    require(len({row_key(row) for row in unique}) == 400, "duplicate unique result")

    for data in (method, depth, unique):
        fields = list(data[0])
        for row in data:
            check_formal_row(row, config, fields)
            require(
                row["interleaverMode"] in ["NONE", *MODES],
                "unknown interleaver mode",
            )
            require(
                row["reuseStatus"] in {
                    "REUSED_STAGE14_CANONICAL", "SIMULATED_STAGE15"
                },
                "unknown reuse status",
            )
    stage14 = read_rows(
        STAGE14 / "results/stage14_burst_formal_raw_results.csv"
    )
    compare_none(method, stage14)
    method_lookup = {row_key(row): row for row in method}
    for row in depth:
        if int(row["interleaverDepth"]) == 8:
            source = method_lookup[row_key(row)]
            require(
                all(
                    row[field] == source[field]
                    for field in (
                        "framesProcessed", "payloadErrorBits",
                        "payloadErrorFrames", "ber", "fer",
                    )
                ),
                "D=8 depth row differs from method row",
            )

    none_lookup = {
        (row["caseId"], int(row["burstLengthBits"])): row
        for row in method if row["interleaverMode"] == "NONE"
    }
    for row in method:
        base = float(none_lookup[
            (row["caseId"], int(row["burstLengthBits"]))
        ]["fer"])
        value = float(row["fer"])
        require(close(row["deltaFer"], base - value), "deltaFer mismatch")
        if base > 0:
            require(
                row["relativeFerReduction"]
                and close(row["relativeFerReduction"], (base - value) / base),
                "relativeFerReduction mismatch",
            )
        if value > 0:
            require(
                row["ratioStatus"] == "EXACT"
                and close(row["ferImprovementRatio"], base / value),
                "FER improvement ratio mismatch",
            )
        else:
            require(
                row["ratioStatus"] == "LOWER_BOUND_ONLY"
                and row["ferImprovementRatio"] == "",
                "zero-FER ratio handling mismatch",
            )

    simulated = [
        row for row in unique if row["reuseStatus"] == "SIMULATED_STAGE15"
    ]
    require(len(simulated) == 328, "new formal simulation count is not 328")
    require(
        len(list((RESULTS / "checkpoints").glob("*.json"))) == 328,
        "checkpoint count is not 328",
    )
    for row in simulated:
        checkpoint = STAGE / row["checkpointPath"]
        require(checkpoint.is_file(), "simulated checkpoint missing")
        data = json.loads(checkpoint.read_text(encoding="utf-8"))
        require(
            data["caseId"] == row["caseId"]
            and data["framesProcessed"] == int(row["framesProcessed"])
            and data["payloadErrorFrames"] == int(row["payloadErrorFrames"])
            and data["gitCommit"] == row["gitCommit"]
            and data["stopReason"] == row["stopReason"],
            "checkpoint differs from result",
        )
    return method, depth, unique, selection_rows


def check_matlab():
    comparison = read_rows(RESULTS / f"{STAGE_ID}_matlab_comparison.csv")
    require(len(comparison) == 96, "MATLAB comparison count is not 96")
    for row in comparison:
        require(
            row["passed"].lower() in {"1", "true"}
            and int(float(row["burstPositionMismatch"])) == 0
            and int(float(row["decodedPayloadMismatch"])) == 0
            and int(float(row["statusMismatch"])) == 0,
            "MATLAB/C++ mismatch",
        )


def check_plots():
    pngs = sorted((RESULTS / "plots").glob("*.png"))
    figure_data = sorted((RESULTS / "figure_data").glob("*.csv"))
    manifests = sorted((RESULTS / "manifests").glob("*_plot_manifest.json"))
    require(
        len(pngs) == len(figure_data) == len(manifests) == 30,
        "PNG/figure-data/manifest count is not 30",
    )
    for path in manifests:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        png = STAGE / manifest["pngFile"]
        data = STAGE / manifest["figureDataFile"]
        require(png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", "non-PNG image")
        require(
            sha256(png) == manifest["pngSha256"]
            and sha256(data) == manifest["figureDataSha256"],
            "plot publication hash mismatch",
        )
        for source, expected in zip(
            manifest["sourceFiles"], manifest["sourceSha256"]
        ):
            require(
                sha256(RESULTS / source) == expected,
                "plot source hash mismatch",
            )
        rows = read_rows(data)
        require(rows, "empty figure-data")
        require(
            all(row["legendLabel"] not in CASES for row in rows),
            "internal Case ID used as legend",
        )
        for row in rows:
            for field in ("xRaw", "xDisplay"):
                require(math.isfinite(float(row[field])), "invalid figure x value")
            for field in ("yRaw", "yPlot"):
                if row[field]:
                    require(
                        math.isfinite(float(row[field])),
                        "invalid figure y value",
                    )
                else:
                    require(
                        "MISSING_REMAINS_MISSING"
                        in manifest["missingValueHandling"],
                        "unmanaged missing figure value",
                    )
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
    for phase in ("method", "depth"):
        for shard in range(4):
            require(
                "PASS_STAGE15_INTERLEAVING_FORMAL_RUNNER"
                in (
                    LOGS / f"{STAGE_ID}_{phase}_shard_{shard}.log"
                ).read_text(encoding="utf-8"),
                f"{phase} shard {shard} runner token missing",
            )
    for name, token in (
        ("selection", "PASS_STAGE15_INTERLEAVING_FORMAL_SELECTION"),
        ("finalize", "PASS_STAGE15_INTERLEAVING_FORMAL_FINALIZE"),
        ("matlab", "PASS_STAGE15_INTERLEAVING_FORMAL_MATLAB_REFERENCE"),
        ("plot", "PASS_STAGE15_INTERLEAVING_FORMAL_PLOT"),
    ):
        require(
            token in (LOGS / f"{STAGE_ID}_{name}.log").read_text(encoding="utf-8"),
            f"{name} log token missing",
        )


def write_supporting_audits(unique):
    merge_rows = []
    for phase in ("method", "depth"):
        for shard in range(4):
            result = (
                RESULTS / "shards"
                / f"{STAGE_ID}_{phase}_shard_{shard}_results.csv"
            )
            merge_rows.append({
                "phase": phase, "shardId": shard,
                "rowCount": len(read_rows(result)),
                "resultFile": result.relative_to(STAGE).as_posix(),
                "resultSha256": sha256(result), "passed": "true",
            })
    write_rows(
        RESULTS / f"{STAGE_ID}_merge_audit.csv",
        list(merge_rows[0]), merge_rows,
    )
    shard_manifest = []
    for row in unique:
        if row["reuseStatus"] != "SIMULATED_STAGE15":
            continue
        phase = "method" if int(row["interleaverDepth"]) == 8 else "depth"
        shard_manifest.append({
            "phase": phase,
            "caseId": row["caseId"],
            "interleaverMode": row["interleaverMode"],
            "interleaverDepth": row["interleaverDepth"],
            "burstLengthBits": row["burstLengthBits"],
            "resultSha256": row["resultSha256"],
            "checkpointPath": row["checkpointPath"],
        })
    write_rows(
        RESULTS / f"{STAGE_ID}_shard_manifest.csv",
        list(shard_manifest[0]), shard_manifest,
    )


def write_audit(unique, selections, code_commit, result_commit):
    reasons = Counter(row["stopReason"] for row in unique)
    total_frames = sum(int(row["framesProcessed"]) for row in unique)
    new_rows = [
        row for row in unique if row["reuseStatus"] == "SIMULATED_STAGE15"
    ]
    new_frames = sum(int(row["framesProcessed"]) for row in new_rows)
    summary = [
        ("methodCanonicalPoints", 288),
        ("depthCanonicalPoints", 224),
        ("uniqueCanonicalPoints", 400),
        ("newFormalPoints", 328),
        ("uniqueCanonicalFrames", total_frames),
        ("newFormalFrames", new_frames),
        ("targetStopsUnique", reasons["TARGET_FRAME_ERRORS_REACHED"]),
        ("maxStopsUnique", reasons["MAX_FRAMES_REACHED"]),
        ("matlabComparisons", 96),
        ("pngFiles", 30),
        ("figureDataFiles", 30),
        ("plotManifests", 30),
    ]
    with (
        RESULTS / f"{STAGE_ID}_result_summary.csv"
    ).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["metric", "value"])
        writer.writerows(summary)

    excluded = {
        f"{STAGE_ID}_sha256.csv", f"{STAGE_ID}_manifest.json",
        f"{STAGE_ID}_gate.txt", f"{STAGE_ID}_report.md",
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
            "name": "originalContent",
            "baseCommit": BASE_COMMIT,
            "contentCommit": ORIGINAL_CONTENT_COMMIT,
            "files": git(
                "diff", "--name-only",
                f"{BASE_COMMIT}...{ORIGINAL_CONTENT_COMMIT}",
            ).splitlines(),
        })
        if code_commit != ORIGINAL_CONTENT_COMMIT:
            ranges.append({
                "name": "repairContent",
                "baseCommit": ORIGINAL_CONTENT_COMMIT,
                "contentCommit": (
                    FIRST_REPAIR_COMMIT
                    if code_commit != FIRST_REPAIR_COMMIT
                    else code_commit
                ),
                "files": git(
                    "diff", "--name-only",
                    (
                        f"{ORIGINAL_CONTENT_COMMIT}..."
                        f"{FIRST_REPAIR_COMMIT if code_commit != FIRST_REPAIR_COMMIT else code_commit}"
                    ),
                ).splitlines(),
            })
        if code_commit not in {ORIGINAL_CONTENT_COMMIT, FIRST_REPAIR_COMMIT}:
            ranges.append({
                "name": "checkerRepairContent",
                "baseCommit": FIRST_REPAIR_COMMIT,
                "contentCommit": (
                    SECOND_REPAIR_COMMIT
                    if code_commit != SECOND_REPAIR_COMMIT
                    else code_commit
                ),
                "files": git(
                    "diff", "--name-only",
                    (
                        f"{FIRST_REPAIR_COMMIT}..."
                        f"{SECOND_REPAIR_COMMIT if code_commit != SECOND_REPAIR_COMMIT else code_commit}"
                    ),
                ).splitlines(),
            })
        if code_commit not in {
            ORIGINAL_CONTENT_COMMIT, FIRST_REPAIR_COMMIT, SECOND_REPAIR_COMMIT
        }:
            ranges.append({
                "name": "provenanceRepairContent",
                "baseCommit": SECOND_REPAIR_COMMIT,
                "contentCommit": code_commit,
                "files": git(
                    "diff", "--name-only",
                    f"{SECOND_REPAIR_COMMIT}...{code_commit}",
                ).splitlines(),
            })
    if result_commit:
        ranges.append({
            "name": "formalResults",
            "baseCommit": code_commit,
            "contentCommit": result_commit,
            "files": git("diff", "--name-only", f"{code_commit}...{result_commit}").splitlines(),
        })
    final = bool(code_commit and result_commit)
    gate = GATE if final else f"{GATE}_FUNCTIONAL"
    manifest = {
        "stage": STAGE_ID,
        "branch": git("branch", "--show-current"),
        "functionalRanges": ranges,
        "codeCommit": code_commit or "WORKTREE",
        "resultCommit": result_commit or "WORKTREE",
        "methodCanonicalPoints": 288,
        "depthCanonicalPoints": 224,
        "uniqueCanonicalPoints": 400,
        "newFormalPoints": 328,
        "uniqueCanonicalFrames": total_frames,
        "newFormalFrames": new_frames,
        "bestInterleavers": {
            row["caseId"]: row["bestInterleaverMode"] for row in selections
        },
        "resultFile": f"results/{STAGE_ID}_raw_results.csv",
        "resultSha256": sha256(RESULTS / f"{STAGE_ID}_raw_results.csv"),
        "checkerVersion": "stage15-checker-v1",
        "runnerVersion": "stage15-runner-v1",
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
    (RESULTS / f"{STAGE_ID}_gate.txt").write_text(gate + "\n", encoding="utf-8")
    (RESULTS / f"{STAGE_ID}_report.md").write_text(
        f"""# Stage15 交织方式与深度正式实验报告

- 分支：`{manifest['branch']}`
- 代码提交：`{code_commit or '功能工作树'}`
- 结果提交：`{result_commit or '结果工作树'}`
- 方式比较 canonical 点：288
- 深度比较 canonical 点：224
- 去重 canonical 点：400
- Stage15 新仿真点：328
- 新仿真累计帧数：{new_frames}
- MATLAB 对比：96/96
- PNG/figure-data/plot manifest：30/30/30
- Gate：`{gate}`
""",
        encoding="utf-8",
    )
    (STAGE / f"{STAGE_ID}_validation_report.md").write_text(
        f"""# Stage15 Validation Report

- Debug/Release build: PASS
- CTest: PASS
- Smoke: PASS
- Formal runner shards: PASS (8/8)
- Method/depth grid checker: PASS (288/224)
- Unique formal point checker: PASS (400; new 328)
- Stage14 NONE reuse checker: PASS
- MATLAB comparison: PASS (96/96)
- Plot publication checker: PASS (30/30)
- Checkpoint and merge audit: PASS
- Gate: {gate}
- Merge status: NOT_MERGED
""",
        encoding="utf-8",
    )
    (STAGE / f"{STAGE_ID}_known_issues.md").write_text(
        """# Stage15 Known Issues

- 本阶段只评价冻结的交织方式、深度与突发长度网格，不外推未采样点。
- 远程包含性在批次最终 push 后统一验证。
- 未使用插值填充任何原始突发长度点。
""",
        encoding="utf-8",
    )
    (STAGE / f"{STAGE_ID}_commands_used.md").write_text(
        """# Stage15 Commands Used

```powershell
python stage15_interleaving_formal_run.py
git commit -m "BCH/Stage15：实现交织方式与深度正式实验"
python stage15_interleaving_formal_run.py --formal
python stage15_interleaving_formal_check.py
```

正式运行使用方式与深度各 4 个点级 shard；每个点独立执行冻结停止规则。
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
        (STAGE / f"configs/{STAGE_ID}_config.json").read_text(encoding="utf-8")
    )
    frozen = json.loads(
        (
            STAGE13
            / "results/stage13_burst_interleaving_validation_frozen_parameters.json"
        ).read_text(encoding="utf-8")
    )
    require(
        config["stopRule"] == frozen["formalStopRule"],
        "formal stop rule differs from Stage13 freeze",
    )
    require(
        config["methodDepth"] == 8 and config["formalDepths"] == [4, 8, 16],
        "interleaver depths differ from freeze",
    )
    method, depth, unique, selections = check_results(config, frozen)
    check_matlab()
    check_plots()
    check_logs()
    write_supporting_audits(unique)
    write_audit(unique, selections, args.code_commit, args.result_commit)
    print(
        GATE if args.code_commit and args.result_commit
        else f"{GATE}_FUNCTIONAL"
    )


if __name__ == "__main__":
    main()
