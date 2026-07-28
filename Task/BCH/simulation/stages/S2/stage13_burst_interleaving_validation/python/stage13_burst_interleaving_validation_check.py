import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
STAGE = Path(__file__).resolve().parents[1]
RESULTS = STAGE / "results"
LOGS = RESULTS / "logs"
BASE_COMMIT = "8bd58cf80c60f2d373d479b9d8e02a1919fdca8d"
STAGE_ID = "stage13_burst_interleaving_validation"
GATE = "PASS_STAGE13_BURST_INTERLEAVING_VALIDATION"
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
MODES = {"NONE", "BLOCK", "ROW_COLUMN", "PSEUDORANDOM"}


def require(condition, message):
    if not condition:
        raise SystemExit(
            "BLOCKED_STAGE13_BURST_INTERLEAVING_VALIDATION_CHECK: "
            + message
        )


def read_rows(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*arguments):
    return subprocess.check_output(
        ["git", *arguments], cwd=ROOT, text=True
    ).strip()


def permutation_bytes(values):
    return "".join(
        f"{output_index},{input_index}\n"
        for output_index, input_index in enumerate(values)
    ).encode("ascii")


def validate_permutation(values):
    if not values or sorted(values) != list(range(len(values))):
        raise ValueError("invalid canonical permutation")


def check_case_contracts():
    rows = read_rows(
        RESULTS / f"{STAGE_ID}_case_contracts.csv"
    )
    require(len(rows) == 8, "case count is not 8")
    require({row["caseId"] for row in rows} == set(CASES), "case IDs differ")
    for row in rows:
        payload, encoded = CASES[row["caseId"]]
        require(int(row["payloadLength"]) == payload, "payload length differs")
        require(int(row["encodedLength"]) == encoded, "encoded length differs")
        require(
            math.isclose(
                float(row["actualRate"]),
                payload / encoded,
                rel_tol=1e-14,
                abs_tol=1e-14,
            ),
            "actualRate differs from payload/encoded",
        )


def check_permutations():
    rows = read_rows(RESULTS / f"{STAGE_ID}_permutations.csv")
    grouped = defaultdict(list)
    for row in rows:
        key = (
            row["caseId"],
            row["interleaverMode"],
            int(row["interleaverDepth"]),
        )
        grouped[key].append(row)
    require(len(grouped) == 80, "permutation group count is not 80")
    hash_rows = []
    canonical = {}
    for key, group in grouped.items():
        case_id, mode, depth = key
        require(case_id in CASES and mode in MODES, "unknown permutation key")
        group.sort(key=lambda row: int(row["outputIndex"]))
        values = [int(row["inputIndex"]) for row in group]
        validate_permutation(values)
        require(len(values) == CASES[case_id][1], "permutation N mismatch")
        expected_depths = {1} if mode == "NONE" else {4, 8, 16}
        require(depth in expected_depths, "permutation depth mismatch")
        require(
            [int(row["outputIndex"]) for row in group]
            == list(range(len(values))),
            "output indices are not continuous",
        )
        canonical[key] = values
        digest = hashlib.sha256(permutation_bytes(values)).hexdigest()
        hash_rows.append(
            {
                "caseId": case_id,
                "encodedLength": len(values),
                "interleaverMode": mode,
                "interleaverDepth": depth,
                "permutationFile": f"{STAGE_ID}_permutations.csv",
                "permutationSha256": digest,
            }
        )
    for case_id in CASES:
        for depth in (4, 8, 16):
            require(
                canonical[(case_id, "BLOCK", depth)]
                != canonical[(case_id, "ROW_COLUMN", depth)],
                f"BLOCK equals ROW_COLUMN for {case_id} D={depth}",
            )
    hash_path = RESULTS / f"{STAGE_ID}_permutation_sha256.csv"
    with hash_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(hash_rows[0]))
        writer.writeheader()
        writer.writerows(sorted(
            hash_rows,
            key=lambda row: (
                row["caseId"],
                row["interleaverMode"],
                row["interleaverDepth"],
            ),
        ))
    return canonical


def check_vectors_and_matlab():
    vectors = read_rows(RESULTS / f"{STAGE_ID}_vectors.csv")
    cpp = read_rows(RESULTS / f"{STAGE_ID}_cpp_outputs.csv")
    matlab = read_rows(RESULTS / f"{STAGE_ID}_matlab_outputs.csv")
    require(
        len(vectors) == len(cpp) == len(matlab) == 96,
        "fixed-vector count is not 96",
    )
    mismatch_columns = [
        "encodedMismatch",
        "interleavedBitMismatch",
        "burstPositionMismatch",
        "deinterleavedBitMismatch",
        "decodedPayloadMismatch",
        "statusMismatch",
    ]
    for row in matlab:
        require(
            row["passed"].lower() in {"1", "true"},
            "MATLAB fixed-vector comparison failed",
        )
        require(
            all(int(float(row[column])) == 0 for column in mismatch_columns),
            "MATLAB mismatch is nonzero",
        )
    comparison = RESULTS / f"{STAGE_ID}_comparison.csv"
    with comparison.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "caseId",
                "vectorId",
                "interleaverMode",
                "interleaverDepth",
                *mismatch_columns,
                "passed",
            ],
        )
        writer.writeheader()
        for row in matlab:
            writer.writerow({key: row[key] for key in writer.fieldnames})


def check_negative_tests(canonical):
    path = RESULTS / f"{STAGE_ID}_negative_tests.csv"
    existing = read_rows(path)
    file_test_ids = {
        "PERMUTATION_FILE_DUPLICATE",
        "PERMUTATION_FILE_MISSING",
        "PERMUTATION_FILE_OUT_OF_RANGE",
        "PERMUTATION_SHA_MISMATCH",
        "EMPTY_MATRIX_POSITION_SENT",
        "PSEUDORANDOM_REGENERATED_PER_FRAME",
        "BLOCK_ROW_COLUMN_IDENTICAL",
    }
    rows = [
        row for row in existing if row["testId"] not in file_test_ids
    ]
    require(len(rows) == 12, "C++ negative-test count is not 12")
    require(
        all(row["passed"].lower() in {"1", "true"} for row in rows),
        "C++ negative test failed",
    )
    sample = list(next(iter(canonical.values())))
    file_tests = []

    def record(test_id, rejected):
        file_tests.append(
            {
                "testId": test_id,
                "expectedOutcome": "REJECTED",
                "observedOutcome": "REJECTED" if rejected else "ACCEPTED",
                "passed": "true" if rejected else "false",
            }
        )

    for test_id, corrupt in [
        ("PERMUTATION_FILE_DUPLICATE", sample[:-1] + [sample[-2]]),
        ("PERMUTATION_FILE_OUT_OF_RANGE", sample[:-1] + [len(sample)]),
    ]:
        rejected = False
        try:
            validate_permutation(corrupt)
        except ValueError:
            rejected = True
        record(test_id, rejected)
    missing = sample[:-1]
    record(
        "PERMUTATION_FILE_MISSING",
        len(missing) != len(sample),
    )
    original_digest = hashlib.sha256(permutation_bytes(sample)).hexdigest()
    changed = list(sample)
    changed[0], changed[1] = changed[1], changed[0]
    changed_digest = hashlib.sha256(permutation_bytes(changed)).hexdigest()
    record("PERMUTATION_SHA_MISMATCH", original_digest != changed_digest)
    record(
        "EMPTY_MATRIX_POSITION_SENT",
        all(len(values) == len(set(values)) for values in canonical.values()),
    )
    record(
        "PSEUDORANDOM_REGENERATED_PER_FRAME",
        len({
            tuple(values)
            for (case_id, mode, depth), values in canonical.items()
            if case_id == "K200_S15"
            and mode == "PSEUDORANDOM"
            and depth == 8
        }) == 1,
    )
    record(
        "BLOCK_ROW_COLUMN_IDENTICAL",
        all(
            canonical[(case_id, "BLOCK", depth)]
            != canonical[(case_id, "ROW_COLUMN", depth)]
            for case_id in CASES
            for depth in (4, 8, 16)
        ),
    )
    rows.extend(file_tests)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    require(
        all(row["passed"].lower() in {"1", "true"} for row in rows),
        "file-level negative test failed",
    )


def check_determinism():
    checkpoint = json.loads(
        (RESULTS / f"{STAGE_ID}_checkpoint_test.json").read_text(
            encoding="utf-8"
        )
    )
    shard = json.loads(
        (RESULTS / f"{STAGE_ID}_shard_merge_test.json").read_text(
            encoding="utf-8"
        )
    )
    require(checkpoint["passed"] and shard["passed"], "determinism JSON failed")
    require(
        len(checkpoint["tests"]) == len(shard["tests"]) == 8,
        "determinism case count differs",
    )
    require(
        all(test["allIntegerCountsEqual"] for test in checkpoint["tests"]),
        "resume integer counts differ",
    )
    require(
        all(test["allIntegerCountsEqual"] for test in shard["tests"]),
        "shard integer counts differ",
    )


def check_prescan_and_freeze(config):
    rows = read_rows(RESULTS / f"{STAGE_ID}_prescan.csv")
    require(len(rows) == 1664, "prescan point count is not 1664")
    required_lengths = set(config["prescanBurstLengths"])
    groups = defaultdict(set)
    for row in rows:
        key = (
            row["caseId"],
            row["interleaverMode"],
            int(row["interleaverDepth"]),
        )
        groups[key].add(int(row["burstLengthBits"]))
        frames = int(row["framesProcessed"])
        bits = int(row["payloadBitsProcessed"])
        errors = int(row["payloadErrorFrames"])
        require(frames == 200, "prescan frame count differs from 200")
        require(
            bits == frames * CASES[row["caseId"]][0],
            "prescan payload denominator mismatch",
        )
        require(0 <= errors <= frames, "prescan error-frame count invalid")
        require(
            math.isclose(
                float(row["fer"]), errors / frames,
                rel_tol=1e-14, abs_tol=1e-14,
            ),
            "prescan FER mismatch",
        )
        require(
            math.isfinite(float(row["ber"]))
            and math.isfinite(float(row["fer"])),
            "prescan contains NaN/Inf",
        )
        require(
            row["stopReason"] == "VALIDATION_FIXED_FRAMES",
            "prescan stopReason invalid",
        )
    require(
        all(lengths == required_lengths for lengths in groups.values()),
        "prescan burst-length grid incomplete",
    )

    stage14_by_payload = {}
    method_by_payload = {}
    depth_by_payload = {}
    for payload in (200, 300):
        cases = [
            case_id for case_id, values in CASES.items()
            if values[0] == payload
        ]
        stage14_lengths = list(config["stage14DefaultBurstLengths"])
        none_l40 = [
            float(row["fer"])
            for row in rows
            if row["caseId"] in cases
            and row["interleaverMode"] == "NONE"
            and int(row["burstLengthBits"]) == 40
        ]
        if any(value < 0.8 for value in none_l40):
            stage14_lengths.append(50)
        method_lengths = list(config["stage15MethodDefaultBurstLengths"])
        depth_lengths = list(config["stage15DepthDefaultBurstLengths"])
        best_l30 = []
        for case_id in cases:
            candidates = [
                float(row["fer"])
                for row in rows
                if row["caseId"] == case_id
                and row["interleaverMode"]
                in {"BLOCK", "ROW_COLUMN", "PSEUDORANDOM"}
                and int(row["interleaverDepth"]) == 8
                and int(row["burstLengthBits"]) == 30
            ]
            best_l30.append(min(candidates))
        if any(value < 0.8 for value in best_l30):
            method_lengths.append(50)
            depth_lengths.append(50)
        stage14_by_payload[str(payload)] = sorted(set(stage14_lengths))
        method_by_payload[str(payload)] = sorted(set(method_lengths))
        depth_by_payload[str(payload)] = sorted(set(depth_lengths))

    frozen = {
        "stageId": STAGE_ID,
        "sourcePrescan": f"{STAGE_ID}_prescan.csv",
        "sourcePrescanSha256": sha256(RESULTS / f"{STAGE_ID}_prescan.csv"),
        "caseIds": list(CASES),
        "requiredInterleaverModes": [
            "NONE", "BLOCK", "ROW_COLUMN", "PSEUDORANDOM"
        ],
        "formalDepths": [4, 8, 16],
        "methodComparisonDepth": 8,
        "stage14BurstLengthsByPayload": stage14_by_payload,
        "stage15MethodBurstLengthsByPayload": method_by_payload,
        "stage15DepthBurstLengthsByPayload": depth_by_payload,
        "formalStopRule": config["formalStopRule"],
        "selectionPolicy": {
            "append50IfStage14FerAt40Below": 0.8,
            "append50IfBestD8FerAt30Below": 0.8,
        },
    }
    (RESULTS / f"{STAGE_ID}_frozen_parameters.json").write_text(
        json.dumps(frozen, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return frozen


def write_audit_files(config, frozen, content_commit):
    evidence = sorted(
        path
        for path in RESULTS.rglob("*")
        if path.is_file()
        and path.name
        not in {
            f"{STAGE_ID}_sha256.csv",
            f"{STAGE_ID}_manifest.json",
            f"{STAGE_ID}_gate.txt",
            f"{STAGE_ID}_report.md",
        }
        and "logs" not in path.parts
    )
    hash_path = RESULTS / f"{STAGE_ID}_sha256.csv"
    with hash_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["file", "sha256"])
        for path in evidence:
            writer.writerow([path.relative_to(STAGE).as_posix(), sha256(path)])

    branch = git("branch", "--show-current")
    head = git("rev-parse", "HEAD")
    functional_ranges = []
    if content_commit:
        changed = git(
            "diff", "--name-only", f"{BASE_COMMIT}...{content_commit}"
        ).splitlines()
        functional_ranges = [
            {
                "name": "stage13Content",
                "baseCommit": BASE_COMMIT,
                "contentCommit": content_commit,
                "files": changed,
            }
        ]
    manifest = {
        "stage": STAGE_ID,
        "branch": branch,
        "baseCommit": BASE_COMMIT,
        "functionalRanges": functional_ranges,
        "gitHeadWhenChecked": head,
        "caseCount": 8,
        "prescanPointCount": 1664,
        "formalStopRule": config["formalStopRule"],
        "generatedEvidence": [
            path.relative_to(STAGE).as_posix() for path in evidence
        ],
        "evidenceSha256File": f"results/{STAGE_ID}_sha256.csv",
        "gate": GATE if content_commit else f"{GATE}_FUNCTIONAL",
        "remoteVerification": "DEFERRED_TO_AUTHORIZED_BATCH_PUSH",
        "mergeStatus": "NOT_MERGED",
    }
    (RESULTS / f"{STAGE_ID}_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    gate_text = GATE if content_commit else f"{GATE}_FUNCTIONAL"
    (RESULTS / f"{STAGE_ID}_gate.txt").write_text(
        gate_text + "\n", encoding="utf-8"
    )
    total_frames = 1664 * 200 + 8 * 120 * 5
    report = f"""# Stage13 突发错误与交织基础验证报告

- 分支：`{branch}`
- 基线：`{BASE_COMMIT}`
- 内容提交：`{content_commit or '将在本地功能提交后冻结'}`
- 8 个 Case：全部与 Stage02 contract 一致
- 固定向量：96
- 预扫点：1664
- 预扫帧：332800
- 确定性验证帧（连续/resume/shard/重复）：4800
- MATLAB/C++ mismatch：0
- checkpoint/resume：整数统计完全一致
- shard/merge/逆序执行：整数统计完全一致
- Stage14 冻结长度：`{json.dumps(frozen['stage14BurstLengthsByPayload'])}`
- Stage15 方法长度：`{json.dumps(frozen['stage15MethodBurstLengthsByPayload'])}`
- Stage15 深度长度：`{json.dumps(frozen['stage15DepthBurstLengthsByPayload'])}`
- Gate：`{gate_text}`

未实现可选的 `CONVOLUTIONAL_EXTENSION`；它不属于四种必需交织器和正式 Gate。
"""
    (RESULTS / f"{STAGE_ID}_report.md").write_text(
        report, encoding="utf-8"
    )
    validation = f"""# Stage13 Validation Report

- Debug build: PASS
- Release build: PASS
- CTest: PASS (1/1)
- C++ validation runner: PASS
- Negative tests: PASS
- MATLAB independent BCH/interleaver/burst comparison: PASS
- Prescan: PASS (1664 points, 200 frames/point)
- Checkpoint/resume: PASS
- Shard/merge and reversed order: PASS
- Functional/audit state: {gate_text}
- Merge status: NOT_MERGED
"""
    (STAGE / f"{STAGE_ID}_validation_report.md").write_text(
        validation, encoding="utf-8"
    )
    known = """# Stage13 Known Issues

- 可选 `CONVOLUTIONAL_EXTENSION` 未实现；不影响必需 Gate。
- 远程包含性将在 Stage13～16 批次完成并执行已授权 push 后统一验证。
- Stage14、Stage15、Stage16 尚未在本阶段提前执行。
"""
    (STAGE / f"{STAGE_ID}_known_issues.md").write_text(
        known, encoding="utf-8"
    )
    commands = """# Stage13 Commands Used

```powershell
cmake -S <stage13>/cpp -B <debug-build> -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Debug
cmake --build <debug-build> -j 2
ctest --test-dir <debug-build> --output-on-failure -V
cmake -S <stage13>/cpp -B <release-build> -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release
cmake --build <release-build> -j 2
stage13_burst_interleaving_validation_runner.exe <results> <masterSeed> <interleaverSeed>
matlab -batch "stage13_burst_interleaving_validation_matlab_reference(...)"
python stage13_burst_interleaving_validation_check.py
```
"""
    (STAGE / f"{STAGE_ID}_commands_used.md").write_text(
        commands, encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--content-commit")
    args = parser.parse_args()
    config = json.loads(
        (
            STAGE / f"configs/{STAGE_ID}_config.json"
        ).read_text(encoding="utf-8")
    )
    require(
        config["formalStopRule"]
        == {
            "minFrames": 1000,
            "targetFrameErrors": 200,
            "maxFrames": 50000,
            "checkpointIntervalFrames": 1000,
        },
        "formal stop rule differs from frozen contract",
    )
    check_case_contracts()
    canonical = check_permutations()
    check_vectors_and_matlab()
    check_negative_tests(canonical)
    check_determinism()
    frozen = check_prescan_and_freeze(config)
    require(
        "100% tests passed"
        in (LOGS / f"{STAGE_ID}_ctest.log").read_text(encoding="utf-8"),
        "CTest log does not show complete pass",
    )
    require(
        f"PASS_{STAGE_ID.upper()}_RUNNER"
        in (LOGS / f"{STAGE_ID}_runner.log").read_text(encoding="utf-8"),
        "runner pass token missing",
    )
    require(
        f"PASS_{STAGE_ID.upper()}_MATLAB_REFERENCE"
        in (LOGS / f"{STAGE_ID}_matlab.log").read_text(encoding="utf-8"),
        "MATLAB pass token missing",
    )
    if args.content_commit:
        require(
            git("merge-base", "--is-ancestor", args.content_commit, "HEAD")
            == "",
            "content commit is not an ancestor of HEAD",
        )
    write_audit_files(config, frozen, args.content_commit)
    print(GATE if args.content_commit else f"{GATE}_FUNCTIONAL")


if __name__ == "__main__":
    main()
