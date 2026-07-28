#!/usr/bin/env python3
import csv
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[6]
OUT_DIR = ROOT / "Task" / "BCH" / "simulation" / "integration" / "stage17_all_channels_integration" / "results"

BRANCHES = [
    {
        "channelLine": "AWGN基础",
        "candidateBranch": "stage01-06-bch-s2-awgn",
        "stageHint": "stage06_awgn_formal",
        "manifest": "Task/BCH/simulation/stages/S2/stage06_awgn_formal/stage06_awgn_formal_manifest.json",
        "expected": ["PASS_STAGE06_AWGN_FORMAL", "PASS_BCH_S2_AWGN_STAGE01_TO_STAGE06"],
    },
    {
        "channelLine": "AWGN高密度",
        "candidateBranch": "stage07-bch-s2-awgn-dense-formal",
        "stageHint": "stage07_awgn_dense_formal",
        "manifest": "Task/BCH/simulation/stages/S2/stage07_awgn_dense_formal/stage07_awgn_dense_formal_manifest.json",
        "expected": ["PASS_STAGE07_AWGN_DENSE_FORMAL", "PASS_BCH_S2_AWGN_DENSE_RERUN"],
    },
    {
        "channelLine": "多径common-SNR",
        "candidateBranch": "stage07-08-bch-s2-multipath",
        "stageHint": "stage08_multipath_formal_common_snr",
        "manifest": "Task/BCH/simulation/stages/S2/stage08_multipath_formal_common_snr/stage08_multipath_formal_common_snr_manifest.json",
        "expected": [
            "PASS_STAGE08_COMMON_SNR_RESULTS_CHECK",
            "PASS_STAGE08_COMMON_SNR_PLOT_CHECK",
            "PASS_STAGE08_MULTIPATH_COMMON_SNR_COMPARISON",
        ],
    },
    {
        "channelLine": "CFO与短时遮挡基础",
        "candidateBranch": "stage09-12-bch-s2-cfo-blockage",
        "stageHint": "stage12_blockage_formal",
        "manifest": "Task/BCH/simulation/stages/S2/stage12_blockage_formal/stage12_blockage_formal_manifest.json",
        "expected": ["PASS_STAGE12_BLOCKAGE_FORMAL", "PASS_BCH_S2_CFO_BLOCKAGE_STAGE09_TO_STAGE12"],
    },
    {
        "channelLine": "CFO与短时遮挡高密度",
        "candidateBranch": "stage10-12-bch-s2-dense-snr-rerun",
        "stageHint": "stage10_cfo_formal;stage12_blockage_formal",
        "manifest": "Task/BCH/simulation/stages/S2/stage10_cfo_formal/stage10_cfo_formal_manifest.json",
        "extraManifest": "Task/BCH/simulation/stages/S2/stage12_blockage_formal/stage12_blockage_formal_manifest.json",
        "expected": [
            "PASS_STAGE10_CFO_FORMAL_DENSE_SNR_0_TO_8_STEP_0P5",
            "PASS_STAGE12_BLOCKAGE_FORMAL_EXPERIMENT_B_DENSE_SNR_0_TO_8_STEP_0P5",
        ],
    },
    {
        "channelLine": "连续突发错误与交织",
        "candidateBranch": "stage13-16-bch-s2-burst-interleaving",
        "stageHint": "stage16_burst_interleaving_comparison",
        "manifest": "Task/BCH/simulation/stages/S2/stage16_burst_interleaving_comparison/results/stage16_burst_interleaving_comparison_manifest.json",
        "expected": ["PASS_STAGE16_BURST_INTERLEAVING_COMPARISON", "PASS_BCH_S2_BURST_INTERLEAVING_STAGE13_TO_STAGE16"],
    },
]

DEPENDENCY_PAIRS = [
    ("stage01-06-bch-s2-awgn", "stage07-bch-s2-awgn-dense-formal"),
    ("stage01-06-bch-s2-awgn", "stage09-12-bch-s2-cfo-blockage"),
    ("stage09-12-bch-s2-cfo-blockage", "stage10-12-bch-s2-dense-snr-rerun"),
    ("stage01-06-bch-s2-awgn", "stage13-16-bch-s2-burst-interleaving"),
    ("stage01-06-bch-s2-awgn", "stage07-08-bch-s2-multipath"),
    ("stage07-bch-s2-awgn-dense-formal", "stage07-08-bch-s2-multipath"),
    ("stage07-bch-s2-awgn-dense-formal", "stage10-12-bch-s2-dense-snr-rerun"),
    ("stage09-12-bch-s2-cfo-blockage", "stage13-16-bch-s2-burst-interleaving"),
]


def git(args, check=True):
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
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc


def show_text(ref, path):
    proc = git(["show", f"{ref}:{path}"], check=False)
    return proc.stdout if proc.returncode == 0 else ""


def list_tree(ref, prefix):
    proc = git(["ls-tree", "-r", "--name-only", ref, prefix], check=False)
    return proc.stdout.splitlines() if proc.returncode == 0 else []


def json_gate(text):
    if not text:
        return ""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return ""
    gates = []
    for key in ("gate", "overallGate", "groupGate"):
        value = data.get(key)
        if value:
            gates.append(str(value))
    if "validationGates" in data and isinstance(data["validationGates"], list):
        gates.extend(str(v) for v in data["validationGates"])
    return ";".join(gates)


def count_csv_rows(ref, path):
    text = show_text(ref, path)
    if not text:
        return ""
    rows = [line for line in text.splitlines() if line.strip()]
    return str(max(0, len(rows) - 1))


def contains_commit(ref, commit):
    if not commit:
        return ""
    proc = git(["merge-base", "--is-ancestor", commit, ref], check=False)
    return "FOUND_IN_HISTORY" if proc.returncode == 0 else "NOT_FOUND_IN_HISTORY"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in BRANCHES:
        branch = item["candidateBranch"]
        ref = f"origin/{branch}"
        exists = git(["rev-parse", "--verify", ref], check=False).returncode == 0
        row = {
            "channelLine": item["channelLine"],
            "candidateBranch": branch,
            "remoteBranchExists": str(exists).upper(),
            "remoteHead": "",
            "mergeBaseWithMain": "",
            "aheadOfMainCommitCount": "",
            "behindMainCommitCount": "",
            "latestCommitMessage": "",
            "stageDirectories": "",
            "gateFiles": "",
            "gateStatus": "MISSING_REMOTE",
            "canonicalResultStatus": "",
            "manifestStatus": "",
            "resultGitCommitStatus": "",
            "diffCheckStatus": "",
            "dependencyBranches": "",
            "recommendedAction": "",
            "blockingReason": "",
        }
        if not exists:
            rows.append(row)
            continue
        row["remoteHead"] = git(["rev-parse", ref]).stdout.strip()
        row["mergeBaseWithMain"] = git(["merge-base", "origin/main", ref]).stdout.strip()
        left_right = git(["rev-list", "--left-right", "--count", f"origin/main...{ref}"]).stdout.strip().split()
        row["behindMainCommitCount"] = left_right[0]
        row["aheadOfMainCommitCount"] = left_right[1]
        row["latestCommitMessage"] = git(["log", "-1", "--format=%h %s", ref]).stdout.strip()
        files = list_tree(ref, "Task/BCH/simulation/stages/S2")
        stage_dirs = sorted({p.split("/")[4] for p in files if p.startswith("Task/BCH/simulation/stages/S2/") and len(p.split("/")) > 4})
        row["stageDirectories"] = ";".join(stage_dirs)
        gate_files = [p for p in files if "gate" in Path(p).name.lower()]
        row["gateFiles"] = ";".join(gate_files)
        manifest_text = show_text(ref, item["manifest"])
        extra_text = show_text(ref, item.get("extraManifest", "")) if item.get("extraManifest") else ""
        gates = ";".join(filter(None, [json_gate(manifest_text), json_gate(extra_text)]))
        row["gateStatus"] = gates
        expected_missing = [gate for gate in item["expected"] if gate not in (manifest_text + extra_text)]
        row["manifestStatus"] = "PASS" if manifest_text and not expected_missing else "FAIL"
        if expected_missing:
            row["blockingReason"] = "missing expected gate: " + ";".join(expected_missing)
        results = [p for p in files if p.endswith(".csv") and ("result" in p.lower() or "summary" in p.lower() or "figure_data" in p.lower())]
        row["canonicalResultStatus"] = f"CSV_FILES={len(results)}"
        raw_results = next((p for p in results if p.endswith("_results.csv") or p.endswith("_raw_results.csv")), "")
        if raw_results:
            row["canonicalResultStatus"] += f";primaryRows={count_csv_rows(ref, raw_results)};primary={raw_results}"
        commit_hint = ""
        for text in (manifest_text, extra_text):
            if text:
                try:
                    data = json.loads(text)
                    commit_hint = data.get("gitCommit") or data.get("commit") or ""
                except json.JSONDecodeError:
                    pass
        row["resultGitCommitStatus"] = contains_commit(ref, commit_hint)
        diff_check = git(["diff", "--check", f"origin/main...{ref}"], check=False)
        row["diffCheckStatus"] = "PASS" if diff_check.returncode == 0 else f"FAIL:{diff_check.stdout.splitlines()[0] if diff_check.stdout else diff_check.stderr.splitlines()[0] if diff_check.stderr else diff_check.returncode}"
        row["recommendedAction"] = "MERGE_AFTER_REVIEW" if row["manifestStatus"] == "PASS" and not row["blockingReason"] else "BLOCKED"
        rows.append(row)

    out_csv = OUT_DIR / "stage17_all_channels_integration_branch_inventory.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    dep_lines = [
        "# Stage17 BCH S2 Integration Dependency Graph",
        "",
        "```mermaid",
        "graph TD",
        '    main["origin/main"]',
    ]
    for item in BRANCHES:
        dep_lines.append(f'    {item["candidateBranch"].replace("-", "_")}["{item["candidateBranch"]}"]')
    dep_lines.append("```")
    dep_lines.append("")
    dep_lines.append("| A | B | A ancestor of B | B ancestor of A |")
    dep_lines.append("|---|---|---|---|")
    mermaid_edges = []
    for a, b in DEPENDENCY_PAIRS:
        fwd = git(["merge-base", "--is-ancestor", f"origin/{a}", f"origin/{b}"], check=False).returncode == 0
        rev = git(["merge-base", "--is-ancestor", f"origin/{b}", f"origin/{a}"], check=False).returncode == 0
        dep_lines.append(f"| `{a}` | `{b}` | {str(fwd).upper()} | {str(rev).upper()} |")
        if fwd:
            mermaid_edges.append((a, b))
        if rev:
            mermaid_edges.append((b, a))
    mermaid = [
        "# Stage17 BCH S2 Integration Dependency Graph",
        "",
        "```mermaid",
        "graph TD",
        '    main["origin/main"]',
    ]
    for a, b in mermaid_edges:
        mermaid.append(f'    {a.replace("-", "_")}["{a}"] --> {b.replace("-", "_")}["{b}"]')
    for item in BRANCHES:
        if item["candidateBranch"] == "stage01-06-bch-s2-awgn":
            mermaid.append(f'    main --> {item["candidateBranch"].replace("-", "_")}["{item["candidateBranch"]}"]')
        if item["candidateBranch"] == "stage07-08-bch-s2-multipath":
            mermaid.append(f'    main --> {item["candidateBranch"].replace("-", "_")}["{item["candidateBranch"]}"]')
    mermaid.append("```")
    mermaid.append("")
    mermaid.extend(dep_lines[-len(DEPENDENCY_PAIRS) - 2 :])
    (OUT_DIR / "stage17_all_channels_integration_dependency_graph.md").write_text("\n".join(mermaid) + "\n", encoding="utf-8")
    print(f"Wrote {out_csv}")
    print(f"Wrote {OUT_DIR / 'stage17_all_channels_integration_dependency_graph.md'}")


if __name__ == "__main__":
    main()
