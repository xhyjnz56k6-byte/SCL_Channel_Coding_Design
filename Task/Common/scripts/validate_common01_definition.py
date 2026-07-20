#!/usr/bin/env python
"""Validate Common-01 frozen definitions.

The script checks the committed definition files. It also supports
`--negative-tests`, which copies the definitions to a temporary tree, applies
known-bad mutations, and verifies that each mutation fails validation.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path


REQUIRED_FILES = [
    "Task/Common/config/global_config.json",
    "Task/Common/config/seed_policy.json",
    "Task/Common/config/stop_rules.json",
    "Task/Common/config/result_schema.json",
    "Task/Common/docs/common_simulation_definition.md",
    "Task/Common/docs/metric_definition.md",
    "Task/Common/docs/seed_policy.md",
    "Task/Common/docs/plot_naming_rules.md",
    "Task/Common/docs/checkpoint_definition.md",
    "Task/Common/docs/terminology.md",
    "Task/Common/stages/stage01_common_definition/stage_plan.md",
    "Task/Common/stages/stage01_common_definition/changed_files.md",
    "Task/Common/stages/stage01_common_definition/validation_report.md",
    "Task/Common/stages/stage01_common_definition/manifest.json",
    "Task/Common/stages/stage01_common_definition/frozen_config.csv",
    "Task/Common/stages/stage01_common_definition/commands_used.md",
    "Task/Common/stages/stage01_common_definition/git_commit.txt",
    "Task/Common/stages/stage01_common_definition/known_issues.md",
]

GLOBAL_FIELDS = [
    "schemaVersion",
    "projectName",
    "stageId",
    "maxCodeBlockLength",
    "motherNoiseLength",
    "supportedPayloadLengths",
    "rateDefinition",
    "lengthDefinitions",
    "bpskMapping",
    "hardDecisionRule",
    "awgnModel",
    "llrConvention",
    "confidenceLevel",
    "confidenceIntervalMethod",
    "zeroErrorPolicy",
    "interleaverPolicy",
    "overwritePolicy",
    "tracePolicy",
]

LENGTH_FIELDS = [
    "K_payload",
    "K_codec_input",
    "N_encoded",
    "N_transmitted",
    "fillerLength",
    "crcLength",
    "tailLength",
    "puncturedLength",
    "shortenedLength",
]

CHECKPOINT_FIELDS = [
    "stageId",
    "runId",
    "experimentId",
    "caseId",
    "snrIndex",
    "nextFrameIndex",
    "framesProcessed",
    "payloadBitsProcessed",
    "bitErrors",
    "frameErrors",
    "payloadSuccessFrames",
    "decoderDeclaredSuccessFrames",
    "undetectedErrorFrames",
    "timingAccumulator",
    "iterationAccumulator",
    "configHash",
    "framePoolHash",
    "noisePolicyVersion",
    "codeVersion",
    "gitCommit",
]


class DuplicateKeyError(ValueError):
    pass


def no_duplicate_object_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle, object_pairs_hook=no_duplicate_object_pairs)


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def validate(root: Path) -> list[str]:
    failures: list[str] = []

    for relative in REQUIRED_FILES:
        require((root / relative).is_file(), f"missing required file: {relative}", failures)
    if failures:
        return failures

    try:
        global_config = load_json(root / "Task/Common/config/global_config.json")
        seed_policy = load_json(root / "Task/Common/config/seed_policy.json")
        stop_rules = load_json(root / "Task/Common/config/stop_rules.json")
        result_schema = load_json(root / "Task/Common/config/result_schema.json")
        manifest = load_json(root / "Task/Common/stages/stage01_common_definition/manifest.json")
    except (json.JSONDecodeError, DuplicateKeyError) as exc:
        return [f"JSON parse failed: {exc}"]

    for field in GLOBAL_FIELDS:
        require(field in global_config, f"global_config missing field: {field}", failures)

    require(global_config.get("projectName") == "SCL_Channel_Coding_Design", "projectName is incorrect", failures)
    require(global_config.get("maxCodeBlockLength") == 1000, "maxCodeBlockLength must equal 1000", failures)
    require(isinstance(global_config.get("motherNoiseLength"), int), "motherNoiseLength must be an integer", failures)
    require(
        global_config.get("motherNoiseLength", 0) >= global_config.get("maxCodeBlockLength", 10**9),
        "motherNoiseLength must be >= maxCodeBlockLength",
        failures,
    )
    payload_lengths = global_config.get("supportedPayloadLengths", [])
    require(200 in payload_lengths and 300 in payload_lengths, "supportedPayloadLengths must contain 200 and 300", failures)

    rate = global_config.get("rateDefinition", {})
    require(rate.get("formula") == "K_payload/N_encoded", "rate formula must be K_payload/N_encoded", failures)
    require(rate.get("numerator") == "K_payload", "rate numerator must be K_payload", failures)
    require(rate.get("denominator") == "N_encoded", "rate denominator must be N_encoded", failures)
    for example in rate.get("examples", []):
        computed = example["K_payload"] / example["N_encoded"]
        require(
            math.isclose(computed, example["expectedRate"], rel_tol=0.0, abs_tol=1e-15),
            f"rate example failed: {example.get('caseId')}",
            failures,
        )
    require(len(rate.get("examples", [])) == 5, "exactly five rate examples are required", failures)

    lengths = global_config.get("lengthDefinitions", {})
    for field in LENGTH_FIELDS:
        require(field in lengths, f"missing length definition: {field}", failures)

    bpsk = global_config.get("bpskMapping", {})
    require(bpsk.get("0") == 1 and bpsk.get("1") == -1, "BPSK mapping must be 0->+1 and 1->-1", failures)

    hard = global_config.get("hardDecisionRule", {})
    hard_text = json.dumps(hard, ensure_ascii=False)
    require(hard.get("zeroBoundaryBit") == 0, "hard decision at y==0 must be bit 0", failures)
    require("receivedSymbol >= 0" in hard_text and "receivedSymbol < 0" in hard_text, "hard decision rules incomplete", failures)

    awgn = global_config.get("awgnModel", {})
    require(awgn.get("sigmaSquaredFormula") == "1/(2*R*10^(EbN0_dB/10))", "AWGN sigma^2 formula mismatch", failures)
    require(awgn.get("rateFormula") == "R=K_payload/N_encoded", "AWGN must reference payload rate", failures)

    llr = global_config.get("llrConvention", {})
    require("2*y_i/sigma^2" in llr.get("formula", ""), "LLR formula mismatch", failures)
    require(llr.get("positiveMeans") == "bit 0" and llr.get("negativeMeans") == "bit 1", "LLR sign mismatch", failures)

    require(global_config.get("confidenceLevel") == 0.95, "confidenceLevel must be 0.95", failures)
    require(
        global_config.get("confidenceIntervalMethod") == "Wilson score interval",
        "confidence interval method must be Wilson score interval",
        failures,
    )

    zero = global_config.get("zeroErrorPolicy", {})
    for field in ["plotBER", "plotFER", "isZeroBitErrorPoint", "isZeroFrameErrorPoint"]:
        require(field in zero.get("requiredFields", []), f"zero error policy missing field: {field}", failures)

    interleaver = global_config.get("interleaverPolicy", {})
    require(interleaver.get("baseAwgnInterleaverEnabled") is False, "base AWGN interleaver must be disabled", failures)
    require(
        interleaver.get("LDPC", {}).get("interleaverAllowed") is False,
        "LDPC interleaver must be forbidden",
        failures,
    )

    overwrite = global_config.get("overwritePolicy", {})
    require(overwrite.get("overwriteExistingResults") is False, "overwriteExistingResults must default to false", failures)

    seed_text = json.dumps(seed_policy, ensure_ascii=False)
    require("noiseGroupId" in seed_text, "noiseGroupId must be defined", failures)
    require(seed_policy.get("reuseNoiseAcrossSnr") is True, "reuseNoiseAcrossSnr must be true", failures)
    require("decoderType" not in seed_policy.get("noiseSeedFields", []), "decoderType must not enter noiseSeedFields", failures)
    require("decoderType" in seed_policy.get("excludedNoiseSeedFields", []), "decoderType must be excluded from noise seed", failures)
    require("frameIndex" in seed_policy.get("noiseSeedFields", []), "frameIndex must enter noiseSeedFields", failures)
    require(
        seed_policy.get("noiseSeedPolicy", {}).get("differentFrameIndexMeansDifferentNoise") is True,
        "different frameIndex principle must be declared in seed_policy.json",
        failures,
    )

    for phase in ["smoke", "prescan", "formalTrial", "formal"]:
        rules = stop_rules.get(phase, {})
        require(rules.get("maxFrames", -1) >= rules.get("minFrames", 10**9), f"{phase}: maxFrames < minFrames", failures)
        require(rules.get("targetFrameErrors", 0) > 0, f"{phase}: targetFrameErrors must be positive", failures)
    stop_expression = stop_rules.get("stopLogic", {}).get("expression", "")
    require("AND" in stop_expression and "OR" in stop_expression, "stop logic must contain correct AND/OR structure", failures)
    for reason in ["TARGET_ERRORS_REACHED", "MAX_FRAMES_REACHED", "MANUAL_STOP", "ERROR_ABORT"]:
        require(reason in stop_rules.get("stopReasons", []), f"missing stop reason: {reason}", failures)

    for field in CHECKPOINT_FIELDS:
        require(field in result_schema.get("checkpointFields", []), f"checkpoint missing field: {field}", failures)
    require(
        result_schema.get("fileSeparation", {}).get("pointResultsFile") == "point_results.csv",
        "point result file must be point_results.csv",
        failures,
    )
    require(
        result_schema.get("fileSeparation", {}).get("curveSummaryFile") == "curve_summary.csv",
        "curve summary file must be curve_summary.csv",
        failures,
    )
    require(
        result_schema.get("fileSeparation", {}).get("codingGainLocation") == "curve_summary.csv",
        "coding gain must belong to curve_summary.csv",
        failures,
    )
    require(
        result_schema.get("plotNamingTemplate") == "{stage}_{code}_{case}_{channel}_{decoder}_{metric}.png",
        "plot naming template missing or incorrect",
        failures,
    )

    common_doc = read_text(root / "Task/Common/docs/common_simulation_definition.md")
    metric_doc = read_text(root / "Task/Common/docs/metric_definition.md")
    seed_doc = read_text(root / "Task/Common/docs/seed_policy.md")
    plot_doc = read_text(root / "Task/Common/docs/plot_naming_rules.md")
    checkpoint_doc = read_text(root / "Task/Common/docs/checkpoint_definition.md")
    docs_all = "\n".join([common_doc, metric_doc, seed_doc, plot_doc, checkpoint_doc])
    for text in [
        "R = K_payload / N_encoded",
        "0 -> +1",
        "1 -> -1",
        "receivedSymbol >= 0 -> bit 0",
        "LLR_i",
        "reuseNoiseAcrossSnr = true",
        "decoderType",
        "Wilson score interval",
        "plotBER",
        "point_results.csv",
        "curve_summary.csv",
        "{stage}_{code}_{case}_{channel}_{decoder}_{metric}.png",
        "overwriteExistingResults = false",
    ]:
        require(text in docs_all, f"docs missing core definition text: {text}", failures)

    require(manifest.get("stage") == "stage01_common_definition", "manifest stage mismatch", failures)
    require(manifest.get("branch") == "stage01-common-definition", "manifest branch mismatch", failures)
    require(manifest.get("gate") == "PASS_COMMON_DEFINITION", "manifest gate mismatch", failures)
    require(
        manifest.get("commitStatus") in ["NOT_COMMITTED", "COMMITTED"],
        "manifest commitStatus must be NOT_COMMITTED or COMMITTED",
        failures,
    )
    if manifest.get("commitStatus") == "COMMITTED":
        require(bool(manifest.get("commitHash")), "manifest commitHash is required when committed", failures)

    return failures


def mutate(path: Path, dotted: str, value_marker) -> None:
    data = load_json(path)
    target = data
    parts = dotted.split(".")
    for part in parts[:-1]:
        target = target[part]
    key = parts[-1]
    if value_marker == "__DELETE__":
        del target[key]
    else:
        target[key] = value_marker
    save_json(path, data)


def run_negative_tests(root: Path) -> list[str]:
    tests = [
        ("reuseNoiseAcrossSnr false", "Task/Common/config/seed_policy.json", "reuseNoiseAcrossSnr", False),
        ("delete K_payload definition", "Task/Common/config/global_config.json", "lengthDefinitions.K_payload", "__DELETE__"),
        ("decoderType in noiseSeedFields", "Task/Common/config/seed_policy.json", "noiseSeedFields", ["masterSeed", "noiseGroupId", "frameIndex", "decoderType"]),
        ("LDPC interleaver allowed", "Task/Common/config/global_config.json", "interleaverPolicy.LDPC.interleaverAllowed", True),
        ("smoke maxFrames less than minFrames", "Task/Common/config/stop_rules.json", "smoke.maxFrames", 10),
        ("wrong rate formula", "Task/Common/config/global_config.json", "rateDefinition.formula", "K_codec_input/N_encoded"),
        ("delete checkpoint required field", "Task/Common/config/result_schema.json", "checkpointFields", [field for field in CHECKPOINT_FIELDS if field != "gitCommit"]),
    ]
    failures: list[str] = []
    for name, relative, dotted, bad_value in tests:
        with tempfile.TemporaryDirectory(prefix="common01_neg_") as temp:
            temp_root = Path(temp)
            shutil.copytree(root / "Task", temp_root / "Task")
            mutate(temp_root / relative, dotted, bad_value)
            result = validate(temp_root)
            if not result:
                failures.append(f"negative test did not fail: {name}")
            else:
                print(f"NEGATIVE TEST EXPECTED FAIL: {name}")
                print(f"  first failure: {result[0]}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Repository root containing Task/Common")
    parser.add_argument("--negative-tests", action="store_true", help="Run expected-failure mutation tests")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    failures = validate(root)

    if args.negative_tests and not failures:
        failures.extend(run_negative_tests(root))

    if failures:
        print("COMMON-01 VALIDATION: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("COMMON-01 VALIDATION: PASS")
    print("Gate: PASS_COMMON_DEFINITION")
    return 0


if __name__ == "__main__":
    sys.exit(main())
