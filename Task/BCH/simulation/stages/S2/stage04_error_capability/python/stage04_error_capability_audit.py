import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[7]
STAGE = Path(__file__).resolve().parents[1]


def require(value, message):
    if not value:
        raise SystemExit(f"BLOCKED_STAGE04_ERROR_CAPABILITY_AUDIT: {message}")


def git(*args):
    result = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, check=False)
    require(result.returncode == 0, result.stderr.strip())
    return result.stdout.strip()


def main():
    manifest = json.loads((STAGE / "stage04_error_capability_manifest.json").read_text(encoding="utf-8"))
    require(git("branch", "--show-current") == manifest["branch"], "branch mismatch")
    require(manifest["gate"] == "PASS_STAGE04_ERROR_CAPABILITY", "Gate mismatch")
    require(manifest["mergeStatus"] == "NOT_MERGED", "merge status mismatch")
    item = manifest["functionalRanges"][0]
    actual = []
    for line in git("diff", "--name-status", item["baseCommit"], item["contentCommit"]).splitlines():
        fields = line.split("\t")
        require(fields[0] == "A", f"unexpected status {line}")
        actual.append(fields[-1])
    require(actual == item["files"], "manifest differs from functional diff")
    require(all(path.startswith("Task/BCH/simulation/stages/S2/stage04_error_capability/")
                for path in actual), "scope violation")
    require(not any(path.endswith((".exe", ".obj", ".pdb")) or "/build/" in path
                    for path in actual), "generated binary committed")
    for relative in manifest["generatedEvidence"]:
        path = STAGE / relative
        require(path.exists() and path.stat().st_size > 0, f"missing evidence {relative}")
    validation = (STAGE / "stage04_error_capability_validation_report.md").read_text(encoding="utf-8")
    for token in ("Pending", "to be run", "NOT_PUSHED", "TO_VERIFY_AFTER_PUSH"):
        require(token not in validation, f"forbidden validation token {token}")
    require((STAGE / "stage04_error_capability_changes.patch").stat().st_size > 0, "changes patch empty")
    print("PASS_STAGE04_ERROR_CAPABILITY_AUDIT")


if __name__ == "__main__":
    main()
