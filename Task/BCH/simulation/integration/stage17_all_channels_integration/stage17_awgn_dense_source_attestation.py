#!/usr/bin/env python3
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
STAGE07 = ROOT / "Task" / "BCH" / "simulation" / "stages" / "S2" / "stage07_awgn_dense_formal"
SOURCE_BRANCH = "origin/stage07-bch-s2-awgn-dense-formal"
STAGE07_PREFIX = "Task/BCH/simulation/stages/S2/stage07_awgn_dense_formal/"
FORBIDDEN_SUFFIXES = (".exe", ".obj", ".pdb")
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def fail(message):
    raise SystemExit("BLOCKED_STAGE17_AWGN_DENSE_SOURCE_ATTESTATION: " + message)


def req(value, message):
    if not value:
        fail(message)


def git(*args, check=True):
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and proc.returncode != 0:
        fail(proc.stderr.strip() or "git command failed: " + " ".join(args))
    return proc


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path):
    req(path.exists(), "missing JSON: " + str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def ancestor(commit, ref):
    return git("merge-base", "--is-ancestor", commit, ref, check=False).returncode == 0


def check_functional_ranges(manifest):
    for item in manifest.get("functionalRanges", []):
        base = item["baseCommit"]
        content = item["contentCommit"]
        req(ancestor(content, "HEAD"), "functional content commit not in integration history: " + content)
        actual = git("diff", "--name-only", base, content).stdout.splitlines()
        req(actual == item["files"], "functional range differs from Git diff: " + item["name"])
        for path in actual:
            req(path.startswith(STAGE07_PREFIX), "functional range escaped Stage07: " + path)
            req("/results/points/" not in path, "point evidence committed in functional range: " + path)
            req("/build/" not in path and "\\build\\" not in path, "build artifact in functional range: " + path)
            req(not path.lower().endswith(FORBIDDEN_SUFFIXES), "binary build artifact in functional range: " + path)


def check_validation_report():
    report = (STAGE07 / "stage07_awgn_dense_formal_validation_report.md").read_text(encoding="utf-8")
    for gate in (
        "PASS_STAGE07_RESUME_EQUIVALENCE",
        "PASS_STAGE07_AWGN_DENSE_FORMAL_RUNNER",
        "PASS_STAGE07_AWGN_DENSE_FORMAL_PLOT",
        "PASS_STAGE07_AWGN_DENSE_PLOT_CHECK",
        "PASS_STAGE07_AWGN_DENSE_FORMAL",
        "PASS_BCH_S2_AWGN_DENSE_RERUN",
    ):
        req(gate in report, "validation report missing gate: " + gate)


def check_canonical_hash_chain():
    results = STAGE07 / "results" / "stage07_awgn_dense_formal_results.csv"
    published = STAGE07 / "published_results" / "stage07_awgn_dense_formal_results.csv"
    plot_manifest_path = STAGE07 / "plots" / "stage07_awgn_dense_formal_plot_manifest.json"
    raw_manifest_path = STAGE07 / "results" / "stage07_awgn_dense_formal_raw_results_manifest.json"
    req(results.exists() and results.stat().st_size > 0, "missing canonical results")
    req(published.exists() and published.stat().st_size > 0, "missing published results")
    req(sha256(results) == sha256(published), "results and published results hash mismatch")
    plot_manifest = load_json(plot_manifest_path)
    raw_manifest = load_json(raw_manifest_path)
    req(plot_manifest["sourceResultsSha256"] == sha256(results), "plot source results hash mismatch")
    req(raw_manifest["resultsSha256"] == sha256(results), "raw results manifest hash mismatch")
    aggregate = STAGE07 / "plots" / plot_manifest["aggregateFigureData"]
    req(plot_manifest["aggregateFigureDataSha256"] == sha256(aggregate), "aggregate figure-data hash mismatch")
    for fig in plot_manifest["figures"]:
        png = STAGE07 / "plots" / fig["png"]
        data = STAGE07 / "plots" / fig["figureData"]
        req(png.read_bytes()[:8] == PNG_MAGIC, "PNG header mismatch: " + fig["png"])
        req(fig["pngSha256"] == sha256(png), "PNG hash mismatch: " + fig["png"])
        req(fig["figureDataSha256"] == sha256(data), "figure-data hash mismatch: " + fig["figureData"])
    commit = plot_manifest.get("gitCommit", "")
    req(commit and ancestor(commit, "HEAD"), "plot manifest gitCommit is not in integration history")


def main():
    source_head = git("rev-parse", SOURCE_BRANCH).stdout.strip()
    req(len(source_head) == 40, "source HEAD is not a full SHA")
    req(source_head == "49ac8aae05d8e99b4354bdd9ee2d1c0885bc797f", "unexpected source HEAD: " + source_head)
    req(ancestor(source_head, "HEAD"), "source HEAD is not an ancestor of integration HEAD")

    manifest_path = STAGE07 / "stage07_awgn_dense_formal_manifest.json"
    manifest = load_json(manifest_path)
    req(manifest["branch"] == "stage07-bch-s2-awgn-dense-formal", "source branch record mismatch")
    req(manifest["gate"] == "PASS_STAGE07_AWGN_DENSE_FORMAL", "Stage07 gate mismatch")
    req(manifest["overallGate"] == "PASS_BCH_S2_AWGN_DENSE_RERUN", "Stage07 overall gate mismatch")
    check_functional_ranges(manifest)
    check_validation_report()
    check_canonical_hash_chain()
    print("PASS_STAGE17_AWGN_DENSE_SOURCE_ATTESTATION")


if __name__ == "__main__":
    main()
