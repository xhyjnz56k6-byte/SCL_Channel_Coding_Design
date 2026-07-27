import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
STAGE = Path(__file__).resolve().parents[1]


def req(value, message):
    if not value:
        raise SystemExit("BLOCKED_STAGE07_AWGN_DENSE_FORMAL_AUDIT: " + message)


def git(*args):
    result = subprocess.run(["git", *args], cwd=ROOT, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    req(result.returncode == 0, result.stderr.strip())
    return result.stdout.strip()


def git_ok(*args):
    return subprocess.run(["git", *args], cwd=ROOT,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def main():
    manifest = json.loads((STAGE / "stage07_awgn_dense_formal_manifest.json").read_text(encoding="utf-8"))
    req(git("branch", "--show-current") == manifest["branch"], "branch mismatch")
    req(manifest["gate"] == "PASS_STAGE07_AWGN_DENSE_FORMAL", "stage gate mismatch")
    req(manifest["overallGate"] == "PASS_BCH_S2_AWGN_DENSE_RERUN", "overall gate mismatch")
    req(manifest["mergeStatus"] == "NOT_MERGED", "merge status mismatch")
    item = manifest["functionalRanges"][0]
    actual = []
    for line in git("diff", "--name-status", item["baseCommit"], item["contentCommit"]).splitlines():
        fields = line.split("\t")
        req(fields[0] == "A", "unexpected functional diff " + line)
        actual.append(fields[-1])
    req(actual == item["files"], "manifest differs from functional diff")
    req(all(x.startswith("Task/BCH/simulation/stages/S2/stage07_awgn_dense_formal/")
            for x in actual), "functional range escaped stage07")
    req(not any("/results/points/" in x or x.endswith((".exe", ".obj", ".pdb")) or "/build/" in x
                for x in actual), "forbidden generated artifact committed")
    validation = (STAGE / "stage07_awgn_dense_formal_validation_report.md").read_text(encoding="utf-8")
    for token in ("Pending", "to be run", "NOT_PUSHED", "TO_VERIFY_AFTER_PUSH"):
        req(token not in validation, token)
    for gate in ("PASS_STAGE07_RESUME_EQUIVALENCE", "PASS_STAGE07_AWGN_DENSE_FORMAL_RUNNER",
                 "PASS_STAGE07_AWGN_DENSE_FORMAL_PLOT", "PASS_STAGE07_AWGN_DENSE_PLOT_CHECK",
                 "PASS_STAGE07_AWGN_DENSE_FORMAL", "PASS_BCH_S2_AWGN_DENSE_RERUN"):
        req(gate in validation, gate + " missing from validation report")
    for relative in manifest["generatedEvidence"]:
        path = STAGE / relative
        req(path.exists() and path.stat().st_size > 0, "missing evidence " + relative)
    req((STAGE / "stage07_awgn_dense_formal_changes.patch").stat().st_size > 0, "empty changes.patch")
    user_plan = "Task/BCH/Plan/第3组计划/v2.0-BCH信道多干扰实验重做.md"
    req((ROOT / user_plan).exists(), "user plan file missing")
    req(not git_ok("ls-files", "--error-unmatch", "--", user_plan),
        "user plan file is tracked")
    print("PASS_STAGE07_AWGN_DENSE_FORMAL_AUDIT")
    print("PASS_BCH_S2_AWGN_DENSE_RERUN")


if __name__ == "__main__":
    main()
