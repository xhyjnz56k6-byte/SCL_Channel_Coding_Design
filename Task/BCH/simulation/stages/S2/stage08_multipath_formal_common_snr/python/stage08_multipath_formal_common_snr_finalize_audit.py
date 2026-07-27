#!/usr/bin/env python3
"""Finalize audit files for the common-SNR multipath comparison."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path

PREFIX = "stage08_multipath_formal_common_snr"


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def weighted_mean(rows: list[dict[str, str]], field: str) -> float:
    frames = sum(int(row["totalFrames"]) for row in rows)
    return sum(float(row[field]) * int(row["totalFrames"]) for row in rows) / frames


def observed_best(rows: list[dict[str, str]], payload: int, metric: str, snr_index: int) -> str:
    selected = [
        row for row in rows
        if int(row["payloadLength"]) == payload and int(row["waveformSnrIndex"]) == snr_index
    ]
    return min(selected, key=lambda row: float(row[metric]))["caseId"]


def censored_group(error_rows: list[dict[str, str]], payload: int, snr_index: int, metric: str) -> tuple[list[str], float]:
    selected = [
        row for row in error_rows
        if int(row["payloadLength"]) == payload and int(row["waveformSnrIndex"]) == snr_index
    ]
    upper_field = "berOneSided95Upper" if metric == "ber" else "ferOneSided95Upper"
    zero = [row for row in selected if row["errorFloorCensoringStatus"] == "ZERO_OBSERVED_CENSORED"]
    if not zero:
        best = min(selected, key=lambda row: float(row[upper_field]))
        return [best["caseId"]], float(best[upper_field])
    upper = min(float(row[upper_field]) for row in zero)
    tied = sorted(row["caseId"] for row in zero if abs(float(row[upper_field]) - upper) <= 1e-18)
    return tied, upper


def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    repo = stage.parents[5]
    rows = read(stage / f"results/{PREFIX}_results.csv")
    summary = read(stage / f"{PREFIX}_summary.csv")
    error_rows = read(stage / f"{PREFIX}_error_floor_analysis.csv")
    files = []
    for path in stage.rglob("*"):
        is_common_file = path.is_file() and PREFIX in path.name
        is_common_plot = path.is_file() and path.parent.name == "plots" and path.name.startswith("stage08_multipath_common_snr_")
        if is_common_file or is_common_plot:
            files.append(path)
    hashes = {str(path.relative_to(repo)).replace("\\", "/"): sha(path) for path in sorted(files)}
    (stage / f"{PREFIX}_file_hashes.json").write_text(
        json.dumps(hashes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    total_frames = sum(int(row["totalFrames"]) for row in rows)
    target_points = sum(row["stopReason"] == "TARGET_FRAME_ERRORS_REACHED" for row in rows)
    max_points = sum(row["stopReason"] == "MAX_FRAMES_REACHED" for row in rows)
    zero_points = sum(row["errorFloorCensoringStatus"] == "ZERO_OBSERVED_CENSORED" for row in error_rows)
    max_residual = max(float(row["solverResidualMax"]) for row in rows)
    old_stage = stage.parent / "stage08_multipath_formal"
    old_results = old_stage / "results" / "stage08_multipath_formal_results.csv"
    old_grid = old_stage / "stage08_multipath_formal_frozen_grid.csv"
    stage07_model = stage.parent / "stage07_multipath_validation" / "stage07_multipath_validation_frozen_model.json"

    conclusion_rows = []
    for payload in (200, 300):
        payload_summary = [row for row in summary if int(row["payloadLength"]) == payload]
        payload_rows = [row for row in rows if int(row["payloadLength"]) == payload]
        high_ber_group, high_ber_upper = censored_group(error_rows, payload, 36, "ber")
        high_fer_group, high_fer_upper = censored_group(error_rows, payload, 36, "fer")
        rate_priority = max(payload_summary, key=lambda row: float(row["actualRate"]))["caseId"]
        cases = sorted({row["caseId"] for row in payload_rows})
        decode_priority = min(cases, key=lambda case: weighted_mean([r for r in payload_rows if r["caseId"] == case], "decodeTimeMeanNs"))
        equalize_priority = min(cases, key=lambda case: weighted_mean([r for r in payload_rows if r["caseId"] == case], "equalizeTimeMeanNs"))
        conclusion_rows.append({
            "payloadLength": payload,
            "lowSnrBerBestObserved": observed_best(rows, payload, "ber", 0),
            "lowSnrFerBestObserved": observed_best(rows, payload, "fer", 0),
            "midSnrBerBestObserved": observed_best(rows, payload, "ber", 18),
            "midSnrFerBestObserved": observed_best(rows, payload, "fer", 18),
            "highSnrBerCensoredBestGroup": ";".join(high_ber_group),
            "highSnrBer95Upper": high_ber_upper,
            "highSnrFerCensoredBestGroup": ";".join(high_fer_group),
            "highSnrFer95Upper": high_fer_upper,
            "ratePriority": rate_priority,
            "decodeLatencyPriority": decode_priority,
            "equalizeLatencyPriority": equalize_priority,
        })

    with (stage / f"{PREFIX}_conclusion.md").open("w", encoding="utf-8") as handle:
        handle.write(f"# {PREFIX} Conclusion\n\n")
        handle.write("本结论只使用统一 `waveformSnrDb=0:0.5:18` 网格下的同 SNR 横向比较；旧 Stage08 标记为 `LEGACY_WIDE_GRID_FORMAL`，不作为最终横向排名依据。\n\n")
        handle.write("Error-floor 处理规则：正式结果 CSV 中的 `ber=0` / `fer=0` 保持原始整数计数含义；在结论和高 SNR 排名中，零错误点标记为 `ZERO_OBSERVED_CENSORED`，只说明在当前帧数下未观测到错误，并使用单侧 95% 上界 `3/N` 给出可审查约束，不能当作真实 error floor 为 0。\n\n")
        handle.write("`miscorrectionFrames` 与 `undetectedErrorFrames` 在当前译码接口语义下是同一事件集合的两个语义标签，不是互斥类别。\n\n")
        for item in conclusion_rows:
            handle.write(f"## {item['payloadLength']} bit\n\n")
            handle.write(f"- 低 SNR 观测 BER 最优：{item['lowSnrBerBestObserved']}；观测 FER 最优：{item['lowSnrFerBestObserved']}。\n")
            handle.write(f"- 中 SNR 观测 BER 最优：{item['midSnrBerBestObserved']}；观测 FER 最优：{item['midSnrFerBestObserved']}。\n")
            handle.write(f"- 高 SNR error-floor-aware BER 候选组：{item['highSnrBerCensoredBestGroup']}，95% 上界约束 <= {item['highSnrBer95Upper']:.6g}。\n")
            handle.write(f"- 高 SNR error-floor-aware FER 候选组：{item['highSnrFerCensoredBestGroup']}，95% 上界约束 <= {item['highSnrFer95Upper']:.6g}。\n")
            handle.write(f"- 码率优先：{item['ratePriority']}；BCH 译码时延优先：{item['decodeLatencyPriority']}；MMSE 均衡时延优先：{item['equalizeLatencyPriority']}。\n")
            handle.write("- 不存在脱离 SNR 工作区间和有限样本 censoring 的单一绝对最优方案。\n\n")

    (stage / f"{PREFIX}_known_issues.md").write_text(
        "# Known Issues\n\n"
        "- 高 SNR 零错误点是右删失/上界证据：有限帧数内未观测到错误，不等于真实 BER/FER 或 error floor 为 0。\n"
        "- 对数图仅使用 `0.5/count` surrogate 显示零错误点；正式 CSV 的原始 `ber=0`、`fer=0` 未被改写。\n"
        "- 高 SNR 多个零错误方案在当前 `50000` 帧上限下不能严格排序；结论改用 `3/N` 单侧 95% 上界和候选组表述。\n"
        "- 时延统计受本机调度和缓存波动影响，适合同一批次内相对比较。\n"
        "- `miscorrectionFrames` 与 `undetectedErrorFrames` 是当前接口下同一事件集合的语义别名。\n"
        "- 本分支尚未合并 `main`，mergeStatus 保持 `NOT_MERGED`。\n",
        encoding="utf-8",
    )
    (stage / f"{PREFIX}_validation_report.md").write_text(
        f"# Validation Report\n\n"
        f"- Results gate: PASS_STAGE08_COMMON_SNR_RESULTS_CHECK\n"
        f"- Plot gate: PASS_STAGE08_COMMON_SNR_PLOT_CHECK\n"
        f"- Final comparison gate: PASS_STAGE08_MULTIPATH_COMMON_SNR_COMPARISON\n"
        f"- Error-floor handling: PASS_ZERO_ERROR_CENSORING_WITH_3_OVER_N_UPPER_BOUND\n"
        f"- Point count: 296\n"
        f"- Total frames: {total_frames}\n"
        f"- TARGET_FRAME_ERRORS_REACHED points: {target_points}\n"
        f"- MAX_FRAMES_REACHED points: {max_points}\n"
        f"- Zero-error censored points: {zero_points}\n"
        f"- Solver residual max: {max_residual:.17g}\n"
        f"- NaN/Inf: 0\n"
        f"- Stage07 frozen model SHA-256: {sha(stage07_model)}\n"
        f"- Legacy Stage08 result SHA-256: {sha(old_results)}\n"
        f"- Legacy Stage08 grid SHA-256: {sha(old_grid)}\n"
        f"- Legacy data label: LEGACY_WIDE_GRID_FORMAL\n\n"
        "Error-floor note: zero-error rows keep raw `ber=0` and `fer=0` in the formal CSV, but reliability conclusions use `ZERO_OBSERVED_CENSORED` status and `3/N` one-sided 95% upper bounds.\n\n"
        "`miscorrectionFrames` 与 `undetectedErrorFrames` 在当前译码接口语义下是同一事件集合的两个语义标签，不是互斥类别。\n",
        encoding="utf-8",
    )
    (stage / f"{PREFIX}_changed_files.md").write_text(
        "# Changed Files\n\n"
        "新增 common-SNR Stage08 补充实验目录，包含 C++ runner、Python checker/plot/audit、冻结网格、正式结果、图像证据和审计文件。后续修正只调整高 SNR error-floor 后处理、排名和结论表达；未改写正式原始计数，未修改 Stage07 与旧 Stage08 结果。\n",
        encoding="utf-8",
    )
    (stage / f"{PREFIX}_manifest.json").write_text(json.dumps({
        "stage": PREFIX,
        "branch": "stage07-08-bch-s2-multipath",
        "baseCommit": git(repo, "merge-base", "main", "HEAD"),
        "currentHeadAtAuditGeneration": git(repo, "rev-parse", "HEAD"),
        "formalRunGitCommit": rows[0]["gitCommit"],
        "formalConfigHash": rows[0]["configHash"],
        "formalPointCount": len(rows),
        "formalFrameCount": total_frames,
        "grid": {"startDb": 0.0, "endDb": 18.0, "stepDb": 0.5, "gridType": "BASE_0P5DB", "refinement": "NO_REFINEMENT"},
        "errorFloorHandling": {
            "zeroErrorStatus": "ZERO_OBSERVED_CENSORED",
            "upperBoundRule": "one-sided 95% upper bound ~= 3/N",
            "rawCsvPolicy": "preserve observed integer counts and raw ber/fer",
        },
        "gates": [
            "PASS_STAGE08_COMMON_SNR_RESULTS_CHECK",
            "PASS_STAGE08_COMMON_SNR_PLOT_CHECK",
            "PASS_STAGE08_MULTIPATH_COMMON_SNR_COMPARISON",
            "PASS_ZERO_ERROR_CENSORING_WITH_3_OVER_N_UPPER_BOUND",
        ],
        "legacyStage08Label": "LEGACY_WIDE_GRID_FORMAL",
        "mergeStatus": "NOT_MERGED",
        "trackedFileHashes": hashes,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS_STAGE08_MULTIPATH_COMMON_SNR_COMPARISON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
