"""Business checker for additive S4-LDPC Stage11R-Stage13R."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
STAGES = ROOT / "Task/LDPC/block/stages"
REQUIRED = [
    "readme.txt", "stage_plan.md", "frozen_config.csv", "changed_files.md",
    "validation_report.md", "known_issues.md", "commands_used.md",
    "manifest.json", "changes.patch", "git_commit.txt",
]


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def check_common(stage: Path) -> None:
    require(stage.is_dir(), f"missing stage: {stage.name}")
    for filename in REQUIRED:
        require((stage / filename).is_file(), f"missing {stage.name}/{filename}")
    require((stage / "results").is_dir() and (stage / "archive").is_dir(),
            f"missing result/archive directory: {stage.name}")
    report = (stage / "validation_report.md").read_text(encoding="utf-8").lower()
    require(not any(token in report for token in
                    ["pending", "to be run", "not_pushed", "to_verify_after_push"]),
            f"unfinished validation state: {stage.name}")
    manifest = json.loads((stage / "manifest.json").read_text(encoding="utf-8"))
    require(manifest["branch"] == "stage01-ldpc"
            and manifest["gateStatus"] == "PASS"
            and manifest["mergeStatus"] == "NOT_MERGED"
            and manifest["formalStarted"] is False, f"manifest state: {stage.name}")
    require(len(manifest["functionalRanges"]) == 1, f"functional range: {stage.name}")
    functional = manifest["functionalRanges"][0]
    actual = subprocess.run(
        ["git", "diff", "--name-only",
         f"{functional['baseCommit']}...{functional['contentCommit']}"],
        cwd=ROOT, check=True, text=True, capture_output=True).stdout.splitlines()
    require(actual == functional["files"], f"functional range diff mismatch: {stage.name}")


def check_stage11() -> None:
    stage = STAGES / "stage11r_alpha_decoder_audit"
    check_common(stage)
    result = stage / "results"
    audit = rows(result / "frame_level_audit.csv")
    require(len(audit) == 10800, f"frame audit rows: {len(audit)}")
    require(all(int(row["nanInfCount"]) == 0 for row in audit), "audit NaN/Inf")
    require({row["earlyStopPolicy"] for row in audit} == {
        "SYNDROME_AFTER_FULL_ITERATION", "ITERATION_LIMIT_ONLY"}, "stop policies")
    breakdown = rows(result / "decoder_outcome_breakdown.csv")
    require(all(sum(int(row[name]) for name in [
        "correct_valid_frames", "wrong_valid_frames",
        "correct_invalid_frames", "wrong_invalid_frames"]) == int(row["frames"])
                for row in breakdown), "four-outcome sum")
    require(any(int(row["wrong_valid_frames"]) > 0 for row in breakdown), "wrong-valid not observed")
    representative = rows(result / "representative_trace_index.csv")
    categories = {row["category"] for row in representative}
    require(categories == {"bp_correct_candidate_wrong", "bp_wrong_candidate_correct",
                           "both_wrong_large_iteration_gap"}, "representative categories")
    require(all(sum(row["category"] == category for row in representative) >= 3
                for category in categories), "representative category count")
    require(rows(result / "representative_trace_details.csv"), "trace details empty")
    require("α=1.00" in (result / "alpha_semantics_note.md").read_text(encoding="utf-8"),
            "alpha semantics")


def check_stage12() -> None:
    stage = STAGES / "stage12r_alpha_curve_selection"
    check_common(stage)
    result = stage / "results"
    points = rows(result / "alpha_candidate_point_results.csv")
    require(len(points) == 150, f"alpha point rows: {len(points)}")
    for n in (480, 560, 640):
        subset = [row for row in points if int(row["actualLength"]) == n]
        labels = {row["series"] for row in subset}
        require(len(labels) == 10 and "BP" in labels and "MS (α=1.00)" in labels,
                f"curve series N{n}")
        for suffix in ["fer", "avgdecodetimeus", "complexity"]:
            stem = result / f"n{n}_alpha_curve_{suffix}"
            require(stem.with_suffix(".png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n"),
                    f"png signature: {stem.name}")
            manifest = json.loads(Path(str(stem) + "_plot_manifest.json").read_text(encoding="utf-8"))
            require(len(manifest["series"]) == 10 and manifest["interpolation"] is False,
                    f"plot manifest: {stem.name}")
            require(Path(str(stem) + "_figure_data.csv").is_file()
                    and Path(str(stem) + "_plot_check.md").is_file(), f"plot sidecars: {stem.name}")
    frozen = json.loads((result / "frozen_alpha_rerun.json").read_text(encoding="utf-8"))
    require(frozen["values"] == {"480": 0.9, "560": 0.9, "640": 0.8}, "rerun alpha")
    require(frozen["alphaOneRetained"] is False, "alpha one retained")


def check_stage13() -> None:
    stage = STAGES / "stage13r_direct_bp_nms_smoke_rerun"
    check_common(stage)
    result = stage / "results"
    points = rows(result / "stage13r_smoke_point_results.csv")
    require(len(points) == 45, f"stage13 point rows: {len(points)}")
    require(all(int(row["frameStart"]) >= 50000 and row["status"] == "PASS"
                and int(row["nanInfCount"]) == 0 for row in points), "smoke separation/status")
    for row in points:
        require(0 <= float(row["berCiLow"]) <= float(row["berCiHigh"]) <= 1, "BER CI")
        require(0 <= float(row["ferCiLow"]) <= float(row["ferCiHigh"]) <= 1, "FER CI")
        require(sum(int(row[name]) for name in [
            "correctValidFrames", "wrongValidFrames",
            "correctInvalidFrames", "wrongInvalidFrames"]) == int(row["frames"]),
                "smoke four-outcome sum")
    for name in ["ber", "fer", "avgiterations", "avgdecodetimeus", "avgcomplexity"]:
        stem = result / f"stage13r_{name}"
        require(stem.with_suffix(".png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n"),
                f"stage13 png: {name}")
        require(Path(str(stem) + "_figure_data.csv").is_file()
                and Path(str(stem) + "_plot_manifest.json").is_file()
                and Path(str(stem) + "_plot_check.md").is_file(), f"stage13 sidecars: {name}")


def main() -> int:
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=ROOT, check=True,
                            text=True, capture_output=True).stdout.strip()
    require(branch == "stage01-ldpc", f"wrong branch: {branch}")
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    check_stage11()
    if mode in {"stage12", "stage13", "all"}:
        check_stage12()
    if mode in {"stage13", "all"}:
        check_stage13()
    forbidden = [path for path in (ROOT / "Task/LDPC").rglob("*")
                 if path.is_dir() and path.name.lower() in
                 {"formal", "formal_coarse", "formal_dense", "waterfall_dense"}]
    require(not forbidden, "formal directory created")
    print(f"PASS_S4_LDPC_ALPHA_RERUN_{mode.upper()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
