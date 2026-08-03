#!/usr/bin/env python3
import json
import pathlib
import subprocess


def git(repo: pathlib.Path, *args: str) -> list[str]:
    result = subprocess.run(["git", *args], cwd=repo, check=True, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return [line for line in result.stdout.splitlines() if line]


def main() -> int:
    script = pathlib.Path(__file__).resolve()
    s5 = script.parents[2]
    repo = script.parents[5]
    stages = sorted((s5 / "stages").glob("stage*"))
    if len(stages) != 12:
        raise RuntimeError(f"expected 12 stages, found {len(stages)}")
    forbidden_tokens = ("Pending", "PENDING", "NOT_PUSHED", "TO_VERIFY_AFTER_PUSH")
    for directory in stages:
        required_files = ["stage_plan.md", "manifest.json", "validation_report.md", "known_issues.md"]
        if directory.name in {"stage09_smoke_validation", "stage10_formal_multichannel_simulation",
                              "stage11_plot_audit_and_final_integration"}:
            required_files.extend(["results", "archive", "readme.txt", "changed_files.md",
                                   "frozen_config.csv", "commands_used.md", "changes.patch"])
        if directory.name == "stage12_known_erasure_cc_validation":
            required_files.extend(["readme.txt", "changed_files.md", "frozen_config.csv",
                                   "commands_used.md", "stage12_parameter_audit.md",
                                   "cpp", "matlab", "comparison", "scripts"])
        for required in required_files:
            expected = directory / required
            valid = expected.is_dir() if required in {"results", "archive", "cpp", "matlab", "comparison", "scripts"} else expected.is_file()
            if not valid:
                raise RuntimeError(f"missing {directory.name}/{required}")
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        if manifest["branch"] != "S5-Compare" or manifest["mergeStatus"] != "NOT_MERGED":
            raise RuntimeError(f"manifest branch/merge mismatch: {directory.name}")
        report = (directory / "validation_report.md").read_text(encoding="utf-8")
        if any(token in report for token in forbidden_tokens):
            raise RuntimeError(f"forbidden unresolved token in {directory.name}/validation_report.md")
    formal = json.loads((s5 / "current" / "config" / "s5_formal_frozen_config.json").read_text(encoding="utf-8"))
    if formal["status"] != "FROZEN_NOT_EXECUTED" or formal["formalExecution"] != "AUTHORIZED_AFTER_PASS_S5_FORMAL_READINESS":
        raise RuntimeError("Formal execution boundary mismatch")
    changed = set(git(repo, "diff", "--name-only"))
    changed.update(git(repo, "diff", "--cached", "--name-only"))
    changed.update(git(repo, "ls-files", "--others", "--exclude-standard"))
    for path in changed:
        normalized = path.replace("\\", "/")
        if not normalized.startswith("Task/Comparison/S5/"):
            raise RuntimeError(f"out-of-scope change: {path}")
        parts = normalized.split("/")
        is_stage_result = len(parts) > 6 and parts[3] == "stages" and parts[5] == "results"
        is_stage12_evidence = (len(parts) > 5 and parts[3] == "stages"
                               and parts[4] == "stage12_known_erasure_cc_validation"
                               and any(part in {"results", "traces", "comparison"} for part in parts[5:]))
        if "build" in parts or ("results" in parts and not is_stage_result and not is_stage12_evidence):
            raise RuntimeError(f"generated path not ignored: {path}")
        if pathlib.PurePosixPath(normalized).suffix.lower() in (".exe", ".obj", ".pdb", ".pyc"):
            raise RuntimeError(f"generated artifact not ignored: {path}")
    print("PASS_S5_STAGE_RECORDS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
