import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[7]
STAGE_DIR = Path(__file__).resolve().parents[1]
MANIFEST = STAGE_DIR / "stage01_foundation_manifest.json"


def require(condition, message):
    if not condition:
        raise SystemExit(f"BLOCKED_STAGE01_FOUNDATION_AUDIT: {message}")


def git(*args):
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(result.returncode == 0, result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(git("branch", "--show-current") == manifest["branch"], "branch mismatch")
    require(manifest["mergeStatus"] == "NOT_MERGED", "mergeStatus mismatch")
    require(manifest["gate"] == "PASS_STAGE01_FOUNDATION", "Gate mismatch")
    ranges = manifest["functionalRanges"]
    require(len(ranges) == 1, "functional range count mismatch")
    item = ranges[0]
    diff_lines = git(
        "diff", "--name-status", item["baseCommit"], item["contentCommit"]
    ).splitlines()
    actual = []
    for line in diff_lines:
        fields = line.split("\t")
        require(fields[0] == "A", f"unexpected functional status: {line}")
        actual.append(fields[-1])
    require(actual == item["files"], "manifest files differ from real Git diff")
    forbidden = (
        "Task/Common/",
        "Task/CC/",
        "Task/LDPC/",
        "Task/BCH/Plan/",
    )
    require(not any(path.startswith(forbidden) for path in actual), "functional scope violation")
    require(
        not any(path.endswith((".exe", ".obj", ".pdb")) or "/build/" in path for path in actual),
        "generated binary entered functional range",
    )
    validation = (STAGE_DIR / "stage01_foundation_validation_report.md").read_text(encoding="utf-8")
    for token in ("Pending", "to be run", "NOT_PUSHED", "TO_VERIFY_AFTER_PUSH"):
        require(token not in validation, f"validation contains forbidden token {token}")
    patch = STAGE_DIR / "stage01_foundation_changes.patch"
    require(patch.exists() and patch.stat().st_size > 0, "changes.patch missing or empty")
    print("PASS_STAGE01_FOUNDATION_AUDIT")


if __name__ == "__main__":
    main()
