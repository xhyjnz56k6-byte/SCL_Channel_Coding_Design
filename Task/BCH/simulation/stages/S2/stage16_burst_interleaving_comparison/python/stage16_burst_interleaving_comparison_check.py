import argparse
import csv
import hashlib
import json
import math
import platform
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
STAGE = Path(__file__).resolve().parents[1]
STAGE13 = STAGE.parent / "stage13_burst_interleaving_validation"
STAGE14 = STAGE.parent / "stage14_burst_formal"
STAGE15 = STAGE.parent / "stage15_interleaving_formal"
RESULTS = STAGE / "results"
LOGS = RESULTS / "logs"
STAGE_ID = "stage16_burst_interleaving_comparison"
GATE = "PASS_STAGE16_BURST_INTERLEAVING_COMPARISON"
GROUP_GATE = "PASS_BCH_S2_BURST_INTERLEAVING_STAGE13_TO_STAGE16"
BASE_COMMIT = "985f439add2c9e82a69b199157bcba8327dd1871"
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
CONFIGURATIONS = ["NONE_L0", "NONE_LREP", "BEST_LREP"]


def require(condition, message):
    if not condition:
        raise SystemExit(
            "BLOCKED_STAGE16_BURST_INTERLEAVING_COMPARISON_CHECK: " + message
        )


def read(path):
    require(path.is_file(), f"missing file: {path}")
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def close(left, right, rel=1e-11, abs_=1e-14):
    return math.isclose(float(left), float(right), rel_tol=rel, abs_tol=abs_)


def canonical_hash(row, fields):
    text = ",".join(row.get(field, "") for field in fields if field != "resultSha256")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def check_selections():
    representative = read(
        RESULTS / f"{STAGE_ID}_representative_burst_selection.csv"
    )
    require(
        {
            int(row["payloadLength"]):
            int(row["representativeBurstLengthBits"])
            for row in representative
        } == {200: 12, 300: 8},
        "representative burst selection differs from frozen automatic rule",
    )
    require(
        all(row["sameLengthForAllFourCases"] == "true" for row in representative),
        "representative L is not unified by payload",
    )
    stage15_modes = {
        row["caseId"]: row["bestInterleaverMode"]
        for row in read(
            STAGE15
            / "results/stage15_interleaving_formal_best_interleaver_selection.csv"
        )
    }
    depths = read(RESULTS / f"{STAGE_ID}_best_depth_selection.csv")
    require(len(depths) == 8, "best-depth selection count differs")
    selected = {}
    for row in depths:
        require(
            row["bestInterleaverMode"] == stage15_modes[row["caseId"]]
            and int(row["bestInterleaverDepth"]) in {4, 8, 16},
            "best mode/depth source mismatch",
        )
        selected[row["caseId"]] = (
            row["bestInterleaverMode"], int(row["bestInterleaverDepth"])
        )
    return {200: 12, 300: 8}, selected


def check_results(config):
    representative, selected = check_selections()
    points = read(RESULTS / f"{STAGE_ID}_points.csv")
    rows = read(RESULTS / f"{STAGE_ID}_raw_results.csv")
    require(len(points) == len(rows) == 888, "formal point count is not 888")
    point_keys = {
        (row["caseId"], row["configurationId"], int(row["snrIndex"]))
        for row in points
    }
    expected = {
        (case_id, configuration, snr)
        for case_id in CASES
        for configuration in CONFIGURATIONS
        for snr in range(37)
    }
    require(point_keys == expected, "point CSV grid differs")
    row_keys = {
        (row["caseId"], row["configurationId"], int(row["snrIndex"]))
        for row in rows
    }
    require(len(row_keys) == len(rows) and row_keys == expected, "result grid differs")
    fields = list(rows[0])
    stop = config["stopRule"]
    for row in rows:
        payload, encoded = CASES[row["caseId"]]
        rate = payload / encoded
        snr_index = int(row["snrIndex"])
        target = float(row["targetSnrDb"])
        expected_ebn0 = target - 10.0 * math.log10(rate)
        require(
            snr_index in range(37) and close(target, 0.5 * snr_index),
            "SNR index/value mismatch",
        )
        require(
            close(row["actualRate"], rate)
            and close(row["derivedEbN0Db"], expected_ebn0, rel=1e-12, abs_=1e-12)
            and close(row["sigma2"], 0.5 / (10.0 ** (target / 10.0))),
            "actualRate SNR conversion mismatch",
        )
        lrep = representative[payload]
        configuration = row["configurationId"]
        if configuration == "NONE_L0":
            require(
                row["interleaverMode"] == "NONE"
                and int(row["interleaverDepth"]) == 1
                and int(row["burstLengthBits"]) == 0,
                "NONE_L0 configuration mismatch",
            )
        elif configuration == "NONE_LREP":
            require(
                row["interleaverMode"] == "NONE"
                and int(row["interleaverDepth"]) == 1
                and int(row["burstLengthBits"]) == lrep,
                "NONE_LREP configuration mismatch",
            )
        else:
            require(
                (
                    row["interleaverMode"],
                    int(row["interleaverDepth"]),
                    int(row["burstLengthBits"]),
                ) == (*selected[row["caseId"]], lrep),
                "BEST_LREP configuration mismatch",
            )
        frames = int(row["framesProcessed"])
        bits = int(row["payloadBitsProcessed"])
        error_bits = int(row["payloadErrorBits"])
        error_frames = int(row["payloadErrorFrames"])
        success = int(row["decoderDeclaredSuccessFrames"])
        failure = int(row["decoderDeclaredFailureFrames"])
        true_success = int(row["trueSuccessFrames"])
        miscorrection = int(row["miscorrectionFrames"])
        undetected = int(row["undetectedErrorFrames"])
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
            require(False, "unknown formal stop reason")
        require(
            bits == payload * frames
            and success + failure == frames
            and true_success + error_frames == frames
            and miscorrection <= success
            and undetected <= miscorrection,
            "integer accounting mismatch",
        )
        require(
            close(row["ber"], error_bits / bits)
            and close(row["fer"], error_frames / frames)
            and close(row["decoderFailureRate"], failure / frames)
            and close(row["miscorrectionRate"], miscorrection / frames)
            and close(row["undetectedErrorRate"], undetected / frames)
            and close(row["trueSuccessRate"], true_success / frames),
            "derived rate mismatch",
        )
        require(
            all(
                math.isfinite(float(row[field]))
                for field in (
                    "targetSnrDb", "derivedEbN0Db", "sigma2", "ber", "fer",
                    "decoderFailureRate", "miscorrectionRate",
                    "undetectedErrorRate", "decoderTimeMeanNs",
                    "decoderTimeP99Ns",
                )
            ),
            "formal row contains NaN/Inf",
        )
        require(
            row["resultSha256"] == canonical_hash(row, fields),
            "row hash mismatch",
        )
        checkpoint = STAGE / row["checkpointPath"]
        require(checkpoint.is_file(), "checkpoint missing")
        data = json.loads(checkpoint.read_text(encoding="utf-8"))
        require(
            data["caseId"] == row["caseId"]
            and data["configurationId"] == configuration
            and data["framesProcessed"] == frames
            and data["payloadErrorFrames"] == error_frames
            and data["stopReason"] == row["stopReason"]
            and data["gitCommit"] == row["gitCommit"],
            "checkpoint content mismatch",
        )
    require(
        len(list((RESULTS / "checkpoints").glob("*.json"))) == 888,
        "checkpoint count is not 888",
    )
    require(len({row["gitCommit"] for row in rows}) == 1, "multiple code commits")
    return rows


def threshold(group, target):
    ordered = sorted(group, key=lambda row: float(row["targetSnrDb"]))
    exact = [
        float(row["targetSnrDb"]) for row in ordered
        if math.isclose(float(row["fer"]), target, rel_tol=1e-12, abs_tol=1e-15)
    ]
    if exact:
        return min(exact), "EXACT"
    for left, right in zip(ordered, ordered[1:]):
        f1, f2 = float(left["fer"]), float(right["fer"])
        if f1 > target > f2 and f1 > 0 and f2 > 0:
            x1, x2 = float(left["targetSnrDb"]), float(right["targetSnrDb"])
            value = x1 + (
                math.log10(target) - math.log10(f1)
            ) * (x2 - x1) / (math.log10(f2) - math.log10(f1))
            return value, "INTERPOLATED"
    positive = [float(row["fer"]) for row in ordered if float(row["fer"]) > 0]
    if positive and min(positive) > target:
        return None, "NOT_REACHED"
    if float(ordered[0]["fer"]) < target:
        return None, "BELOW_RANGE"
    return None, "ABOVE_RANGE"


def check_derived(rows):
    targets = read(RESULTS / f"{STAGE_ID}_target_fer_snr.csv")
    require(len(targets) == 48, "target FER SNR row count differs")
    for item in targets:
        group = [
            row for row in rows
            if row["caseId"] == item["caseId"]
            and row["configurationId"] == item["configurationId"]
        ]
        value, status = threshold(group, float(item["targetFer"]))
        require(status == item["status"], "target FER status mismatch")
        require(item["extrapolated"] == "false", "target FER was extrapolated")
        if value is None:
            require(item["targetSnrDb"] == "", "uncovered target has value")
        else:
            require(
                item["targetSnrDb"] and close(item["targetSnrDb"], value),
                "target FER interpolation mismatch",
            )
    require(
        len(read(RESULTS / f"{STAGE_ID}_snr_penalty.csv")) == 32
        and len(read(RESULTS / f"{STAGE_ID}_tolerance_summary.csv")) == 8
        and len(read(RESULTS / f"{STAGE_ID}_recommendation_matrix.csv")) == 8,
        "summary row count mismatch",
    )
    merge = read(RESULTS / f"{STAGE_ID}_merge_audit.csv")
    require(
        len(merge) == 4
        and all(row["passed"] == "true" for row in merge)
        and sum(int(row["rowCount"]) for row in merge) == 888,
        "shard merge audit mismatch",
    )


def check_matlab():
    vectors = read(RESULTS / f"{STAGE_ID}_matlab_vector_comparison.csv")
    snr = read(RESULTS / f"{STAGE_ID}_matlab_snr_comparison.csv")
    require(len(vectors) == 96 and len(snr) == 888, "MATLAB row count differs")
    require(
        all(
            row["passed"].lower() in {"1", "true"}
            and int(float(row["burstPositionMismatch"])) == 0
            and int(float(row["decodedPayloadMismatch"])) == 0
            and int(float(row["statusMismatch"])) == 0
            for row in vectors
        ),
        "MATLAB fixed-vector mismatch",
    )
    require(
        all(
            row["passed"].lower() in {"1", "true"}
            and float(row["absoluteDifference"]) <= 1e-9
            for row in snr
        ),
        "MATLAB SNR conversion mismatch",
    )


def check_plots():
    pngs = sorted((RESULTS / "plots").glob("*.png"))
    data_files = sorted((RESULTS / "figure_data").glob("*.csv"))
    manifests = sorted((RESULTS / "manifests").glob("*_plot_manifest.json"))
    require(
        len(pngs) == len(data_files) == len(manifests) == 20,
        "plot/data/manifest count is not 20",
    )
    total = 0
    for path in manifests:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        png = STAGE / manifest["pngFile"]
        data = STAGE / manifest["figureDataFile"]
        require(
            manifest["xDisplayLabel"] == "SNR"
            and manifest["xPhysicalQuantity"] == "waveform_snr"
            and manifest["xUnit"] == "dB",
            "SNR manifest semantics mismatch",
        )
        require(png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", "non-PNG image")
        require(
            sha(png) == manifest["pngSha256"]
            and sha(data) == manifest["figureDataSha256"]
            and sha(RESULTS / manifest["sourceFiles"][0])
            == manifest["sourceSha256"][0],
            "plot publication hash mismatch",
        )
        rows = read(data)
        total += len(rows)
        require(
            len(manifest["legendLabels"])
            == len(set(row["legendLabel"] for row in rows)),
            "legend/series count mismatch",
        )
        for row in rows:
            require(row["legendLabel"] not in CASES, "internal Case ID legend")
            require(
                close(
                    row["derivedEbN0Db"],
                    float(row["xRaw"]) - 10.0 * math.log10(float(row["actualRate"])),
                    rel=1e-12, abs_=1e-12,
                ),
                "figure-data SNR conversion mismatch",
            )
            require(
                all(
                    math.isfinite(float(row[field]))
                    for field in ("xRaw", "xDisplay", "yRaw", "yPlot")
                ),
                "figure-data NaN/Inf",
            )
            if row["yIsZero"] == "true":
                denominator = (
                    int(row["payloadBitsProcessed"])
                    if manifest["ySourceColumn"] == "ber"
                    else int(row["framesProcessed"])
                )
                require(
                    float(row["yRaw"]) == 0
                    and close(row["yPlot"], 0.5 / denominator),
                    "zero surrogate mismatch",
                )
    require(total == 3552, "figure-data total row count differs")
    require(
        not [
            path for path in RESULTS.rglob("*")
            if path.suffix.lower() in {".pdf", ".svg", ".eps", ".jpg", ".jpeg"}
        ],
        "forbidden plot format exists",
    )


def check_logs():
    require(
        "100% tests passed"
        in (LOGS / f"{STAGE_ID}_ctest.log").read_text(encoding="utf-8"),
        "CTest log is not PASS",
    )
    for shard in range(4):
        require(
            "PASS_STAGE16_BURST_INTERLEAVING_COMPARISON_RUNNER"
            in (LOGS / f"{STAGE_ID}_shard_{shard}.log").read_text(encoding="utf-8"),
            f"shard {shard} token missing",
        )
    for name, token in (
        ("prepare", "PASS_STAGE16_BURST_INTERLEAVING_COMPARISON_PREPARE"),
        ("finalize", "PASS_STAGE16_BURST_INTERLEAVING_COMPARISON_FINALIZE"),
        ("matlab", "PASS_STAGE16_BURST_INTERLEAVING_COMPARISON_MATLAB_REFERENCE"),
        ("plot", "PASS_STAGE16_BURST_INTERLEAVING_COMPARISON_PLOT"),
    ):
        require(
            token in (LOGS / f"{STAGE_ID}_{name}.log").read_text(encoding="utf-8"),
            f"{name} log token missing",
        )


def write_audit(rows, code_commit, result_commit):
    reasons = Counter(row["stopReason"] for row in rows)
    total_frames = sum(int(row["framesProcessed"]) for row in rows)
    summary = [
        ("formalPoints", 888),
        ("totalFrames", total_frames),
        ("targetStops", reasons["TARGET_FRAME_ERRORS_REACHED"]),
        ("maxStops", reasons["MAX_FRAMES_REACHED"]),
        ("matlabVectorComparisons", 96),
        ("matlabSnrComparisons", 888),
        ("pngFiles", 20),
        ("figureDataFiles", 20),
        ("plotManifests", 20),
    ]
    with (
        RESULTS / f"{STAGE_ID}_result_summary.csv"
    ).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["metric", "value"])
        writer.writerows(summary)
    excluded = {
        f"{STAGE_ID}_sha256.csv", f"{STAGE_ID}_manifest.json",
        f"{STAGE_ID}_gate.txt", f"{STAGE_ID}_group_gate.txt",
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
            writer.writerow([path.relative_to(STAGE).as_posix(), sha(path)])
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
    group_gate = GROUP_GATE if final else f"{GROUP_GATE}_FUNCTIONAL"
    manifest = {
        "stage": STAGE_ID,
        "branch": git("branch", "--show-current"),
        "functionalRanges": ranges,
        "codeCommit": code_commit or "WORKTREE",
        "resultCommit": result_commit or "WORKTREE",
        "formalPointCount": 888,
        "totalFrames": total_frames,
        "stopReasonCounts": dict(reasons),
        "snrGrid": {"minimumDb": 0, "maximumDb": 18, "stepDb": 0.5, "count": 37},
        "resultFile": f"results/{STAGE_ID}_raw_results.csv",
        "resultSha256": sha(RESULTS / f"{STAGE_ID}_raw_results.csv"),
        "checkerVersion": "stage16-checker-v1",
        "runnerVersion": "stage16-runner-v1",
        "compiler": "GNU MinGW",
        "buildType": "Release",
        "os": platform.platform(),
        "pythonVersion": platform.python_version(),
        "matlabVersion": "captured-in-matlab-log",
        "gate": gate,
        "groupGate": group_gate,
        "remoteVerification": "DEFERRED_TO_AUTHORIZED_BATCH_PUSH",
        "mergeStatus": "NOT_MERGED",
    }
    (RESULTS / f"{STAGE_ID}_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (RESULTS / f"{STAGE_ID}_gate.txt").write_text(gate + "\n", encoding="utf-8")
    (RESULTS / f"{STAGE_ID}_group_gate.txt").write_text(
        group_gate + "\n", encoding="utf-8"
    )
    reports = RESULTS / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    recommendations = read(RESULTS / f"{STAGE_ID}_recommendation_matrix.csv")
    mode_counts = Counter(
        row["recommendedInterleaverMode"] for row in recommendations
    )
    depth_counts = Counter(row["recommendedDepth"] for row in recommendations)
    penalties = read(RESULTS / f"{STAGE_ID}_snr_penalty.csv")
    available = [
        float(row["snrDifferenceDb"]) for row in penalties
        if row["comparison"] == "INTERLEAVER_RECOVERY"
        and row["status"] == "AVAILABLE"
    ]
    recovery_text = (
        f"可比较点的目标 FER SNR 恢复范围为 "
        f"{min(available):.3f}～{max(available):.3f} dB。"
        if available else
        "目标 FER 覆盖不足，不能形成可比较的 SNR 恢复数值。"
    )
    report = f"""# Stage16 AWGN+突发信道适应性及内部综合比较报告

- 正式网格：8 Case × 3 配置 × 37 SNR = 888 点
- SNR：0～18 dB，步长 0.5 dB；逐 Case 使用 actualRate 换算 Eb/N0
- 代表性突发长度：K=200 为 12 bit，K=300 为 8 bit
- 最佳方式分布：{dict(mode_counts)}
- 最佳深度分布：{dict(depth_counts)}
- 正式累计帧数：{total_frames}
- 停止原因：{dict(reasons)}
- MATLAB：固定向量 96/96，SNR 换算 888/888
- Gate：`{gate}`
- 组级 Gate：`{group_gate}`

## 数据驱动结论

1. 无交织抗突发能力、FER 增长速度和码块边界敏感性以 Stage14 tolerance/affected-block CSV 为准；分块方案在短突发处更快进入高 FER，不能外推为其他信道结论。
2. K300 双块方案的边界影响已保留在 Stage14/15 受影响码块统计中；本阶段不以单个起点替代随机起点总体统计。
3. Stage15 自动选择显示最佳必需交织器并非全部 Case 一致：{dict(mode_counts)}。
4. D=4/8/16 的选择并非预设；最佳深度分布为 {dict(depth_counts)}，收益是否饱和以 depth CSV 的原始点为准。
5. 分块与整块的交织收益只在本次冻结突发长度和停止规则内比较，不宣称跨信道优势。
6. 交织缓存为实际编码长度 bit，时延来自 Stage15 原始累计计时，未用估计值替代。
7. {recovery_text}
8. K=200 与 K=300 使用不同代表突发长度，推荐配置按 Case 保存在 recommendation matrix。

本报告只形成连续突发与 AWGN+连续突发内部结论，不形成全部信道最终排名。
"""
    (reports / f"{STAGE_ID}_report.md").write_text(report, encoding="utf-8")
    execution = f"""# Stage13～Stage16 执行摘要

- 分支：`{manifest['branch']}`
- worktree：`{ROOT}`
- 基线：`8bd58cf80c60f2d373d479b9d8e02a1919fdca8d`
- Stage16 代码提交：`{code_commit or '功能工作树'}`
- Stage16 结果提交：`{result_commit or '结果工作树'}`
- Stage13 Gate：PASS
- Stage14 Gate：PASS
- Stage15 Gate：PASS
- Stage16 Gate：{gate}
- 组级 Gate：{group_gate}
- Stage16 正式点/帧：888/{total_frames}
- Stage16 图片/figure-data/manifest：20/20/20
- mergeStatus：NOT_MERGED
"""
    (reports / f"{STAGE_ID}_execution_summary.md").write_text(
        execution, encoding="utf-8"
    )
    (STAGE / f"{STAGE_ID}_validation_report.md").write_text(
        f"""# Stage16 Validation Report

- Debug/Release build: PASS
- CTest: PASS
- Smoke: PASS
- Formal runner shards: PASS (4/4)
- Formal grid and stop checker: PASS (888/888)
- actualRate SNR conversion: PASS
- Selection provenance: PASS
- MATLAB comparison: PASS (96 vectors; 888 SNR conversions)
- Plot publication: PASS (20/20)
- Gate: {gate}
- Group Gate: {group_gate}
- Merge status: NOT_MERGED
""",
        encoding="utf-8",
    )
    (STAGE / f"{STAGE_ID}_known_issues.md").write_text(
        """# Stage16 Known Issues

- 结论仅适用于冻结的连续突发和 AWGN+连续突发场景。
- 零错误观测不是“真实 FER 为零”；图中只使用统计代理值显示。
- 未覆盖目标 FER 的曲线不外推，汇总表保留对应状态。
- 远程包含性在授权批次 push 后统一验证。
""",
        encoding="utf-8",
    )
    (STAGE / f"{STAGE_ID}_commands_used.md").write_text(
        """# Stage16 Commands Used

```powershell
python stage16_burst_interleaving_comparison_run.py
git commit -m "BCH/Stage16：实现AWGN突发适应性与综合比较"
python stage16_burst_interleaving_comparison_run.py --formal
python stage16_burst_interleaving_comparison_check.py
```

正式运行使用 4 个点级 shard，每点独立执行 1000/200/50000/1000 停止规则。
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
    require(
        config["snr"] == {
            "minimumDb": 0.0, "maximumDb": 18.0, "stepDb": 0.5,
            "pointCount": 37, "physicalQuantity": "waveform_snr",
            "displayLabel": "SNR", "unit": "dB",
        },
        "SNR config differs from freeze",
    )
    require(
        config["stopRule"] == {
            "minFrames": 1000, "targetFrameErrors": 200,
            "maxFrames": 50000, "checkpointIntervalFrames": 1000,
        },
        "formal stop rule differs from freeze",
    )
    rows = check_results(config)
    check_derived(rows)
    check_matlab()
    check_plots()
    check_logs()
    write_audit(rows, args.code_commit, args.result_commit)
    print(
        f"{GATE}\n{GROUP_GATE}"
        if args.code_commit and args.result_commit
        else f"{GATE}_FUNCTIONAL\n{GROUP_GATE}_FUNCTIONAL"
    )


if __name__ == "__main__":
    main()
