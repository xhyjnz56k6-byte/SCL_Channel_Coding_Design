#!/usr/bin/env python3
"""Validate the frozen CC Stage01 contract using only the Python standard library."""

from __future__ import annotations

import argparse
import copy
import csv
import json
import math
from pathlib import Path
from typing import Any


STAGE = "stage01_cc_contract"
GATE = "PASS_STAGE01_CC_CONTRACT"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def output_bits(state: int, input_bit: int) -> tuple[int, int]:
    m1 = (state >> 5) & 1
    m2 = (state >> 4) & 1
    m3 = (state >> 3) & 1
    m5 = (state >> 1) & 1
    m6 = state & 1
    g1 = input_bit ^ m1 ^ m2 ^ m3 ^ m6
    g2 = input_bit ^ m2 ^ m3 ^ m5 ^ m6
    return g1, g2


def validate_contract(contract: dict[str, Any], schema: dict[str, Any]) -> None:
    main = contract["mainScenario"]
    require(contract["schemaVersion"] == "cc.s3.contract.v1", "contract schema version")
    require(contract["stage"] == STAGE, "stage id")
    require(main["constraintLength"] == 7, "constraint length")
    require(main["memory"] == main["constraintLength"] - 1 == 6, "memory")
    require(main["stateCount"] == 2 ** main["memory"] == 64, "state count")
    require(main["generator1Octal"] == "171", "generator1 octal")
    require(main["generator2Octal"] == "133", "generator2 octal")
    require(main["generator1Binary"] == format(int("171", 8), "07b") == "1111001", "generator1 binary")
    require(main["generator2Binary"] == format(int("133", 8), "07b") == "1011011", "generator2 binary")
    require(main["initialState"] == 0, "initial state")
    require(main["tailLength"] == main["memory"] == 6, "tail length")

    block = contract["blockZeroTail"]
    require(block["K_payload"] == 300, "payload length")
    require(block["K_codec_input"] == block["K_payload"] + main["tailLength"] == 306, "codec input")
    require(block["N_mother"] == 2 * block["K_codec_input"] == 612, "mother length")
    require(block["N_transmittedMother"] == 612, "mother transmitted length")
    expected_rate = block["K_payload"] / block["N_transmittedMother"]
    require(math.isclose(block["actualRateMother"], expected_rate, rel_tol=0.0, abs_tol=1e-15), "actual rate")
    require(block["tailBits"] == [0] * 6, "zero tail")
    require(block["terminationState"] == 0, "termination state")

    bit_order = contract["bitOrder"]
    require(bit_order["nextStateFormula"] == "((inputBit & 1) << 5) | (stateIndex >> 1)", "next-state formula")
    require(bit_order["branchOutputOrder"] == ["g1_171", "g2_133"], "output order")
    require(bit_order["motherSerialization"] == "TIME_MAJOR_G1_THEN_G2", "serialization")
    expected_vectors = {
        (0, 0): (0, 0, 0),
        (0, 1): (32, 1, 1),
        (32, 0): (16, 1, 0),
        (32, 1): (48, 0, 1),
        (1, 0): (0, 1, 1),
        (1, 1): (32, 0, 0),
    }
    for (state, input_bit), (expected_next, expected_g1, expected_g2) in expected_vectors.items():
        next_state = ((input_bit & 1) << 5) | (state >> 1)
        g1, g2 = output_bits(state, input_bit)
        require((next_state, g1, g2) == (expected_next, expected_g1, expected_g2), f"known vector {state}/{input_bit}")

    bpsk = contract["bpsk"]
    require(bpsk["bit0Symbol"] == 1.0 and bpsk["bit1Symbol"] == -1.0, "BPSK mapping")
    require(bpsk["hardDecisionZeroInclusive"] is True, "hard zero decision")
    require(bpsk["positiveLlrMeansBit"] == 0, "LLR sign")

    snr = contract["snr"]
    require(snr["definition"] == "BPSK_SYMBOL_ES_OVER_N0", "SNR definition")
    require(snr["axisLabel"] == "SNR (dB)", "SNR label")
    for snr_db in (-2.0, 0.0, 3.5):
        sigma_squared = 1.0 / (2.0 * 10.0 ** (snr_db / 10.0))
        ebn0_db = snr_db - 10.0 * math.log10(expected_rate)
        reconstructed = ebn0_db + 10.0 * math.log10(expected_rate)
        require(math.isfinite(sigma_squared) and sigma_squared > 0.0, "finite sigma squared")
        require(math.isclose(reconstructed, snr_db, abs_tol=1e-12), "SNR/EbN0 conversion")

    metrics = contract["metrics"]
    require(metrics["hardBranchMetric"] == "MASKED_HAMMING_DISTANCE", "hard metric")
    require(metrics["softFloatBranchMetric"] == "MASKED_RECEIVED_SYMBOL_EUCLIDEAN_SQUARED", "soft metric")
    require(metrics["tieBreaking"] == ["LOWER_PATH_METRIC", "LOWER_PREDECESSOR_STATE", "LOWER_INPUT_BIT"], "tie breaking")
    require(metrics["normalization"] == "SUBTRACT_MIN_FINITE_EVERY_TRELLIS_STEP", "normalization")
    require(metrics["missingHardBitPolicy"] == "EXCLUDE_WITH_OBSERVED_MASK", "missing hard bit policy")
    require(metrics["missingSoftLlr"] == 0.0, "neutral LLR")
    require(metrics["nonFinitePolicy"] == "ERROR_ABORT", "non-finite policy")

    puncture = contract["puncturingInterface"]
    require(puncture["maskOrder"] == "TIME_MAJOR_G1_THEN_G2", "puncture order")
    require(puncture["tailPolicy"] == "CONTINUE_CURRENT_PATTERN_PHASE", "tail puncture phase")
    require(puncture["continuousSlotPolicy"] == "CARRY_PATTERN_PHASE", "slot puncture phase")
    require(puncture["nTransmittedPolicy"] == "COUNT_RETAINED_BITS", "transmitted length policy")

    stop = contract["stopRules"]
    require(stop["formal"] == {
        "minFrames": 5000,
        "targetFrameErrors": 200,
        "maxFrames": 50000,
        "checkpointIntervalFrames": 1000,
    }, "formal stop rules")
    require("AND payloadErrorFrames" in stop["expression"], "stop-rule conjunction")

    required_point = set(schema["pointResultRequiredFields"])
    required_checkpoint = set(schema["checkpointRequiredFields"])
    for field in (
        "snrDb", "ebN0Db", "actualRate", "sigmaSquared", "framesProcessed",
        "payloadBitErrors", "payloadErrorFrames", "BER", "FER",
        "p95DecodeTime_us", "normalizedGoodput",
    ):
        require(field in required_point, f"point field {field}")
    for field in ("nextFrameIndex", "configHash", "encoderState", "puncturePhase", "decoderStateMetricState"):
        require(field in required_checkpoint, f"checkpoint field {field}")
    require(schema["commonCompatibility"]["codeRateRule"] == "codeRate == actualRate", "common rate mirror")
    require(set(schema["stopReasonEnum"]) == set(stop["stopReasons"]), "stop reason enum")
    require(schema["forbiddenGenericResultNames"] == [
        "result.csv", "results.csv", "figure1.png", "plot.png", "output.png", "test.csv"
    ], "forbidden names")


def run_negative_mutations(contract: dict[str, Any], schema: dict[str, Any]) -> list[tuple[str, bool]]:
    mutations: list[tuple[str, dict[str, Any], dict[str, Any]]] = []

    bad = copy.deepcopy(contract)
    bad["mainScenario"]["stateCount"] = 32
    mutations.append(("reject_wrong_state_count", bad, schema))

    bad = copy.deepcopy(contract)
    bad["mainScenario"]["generator1Binary"] = "1001111"
    mutations.append(("reject_reversed_generator_bits", bad, schema))

    bad = copy.deepcopy(contract)
    bad["blockZeroTail"]["actualRateMother"] = 0.5
    mutations.append(("reject_theoretical_rate_as_actual", bad, schema))

    bad = copy.deepcopy(contract)
    bad["metrics"]["missingHardBitPolicy"] = "FILL_ZERO_AS_OBSERVATION"
    mutations.append(("reject_missing_hard_as_zero", bad, schema))

    bad_schema = copy.deepcopy(schema)
    bad_schema["pointResultRequiredFields"].remove("sigmaSquared")
    mutations.append(("reject_missing_sigma_squared", contract, bad_schema))

    results: list[tuple[str, bool]] = []
    for name, mutated_contract, mutated_schema in mutations:
        rejected = False
        try:
            validate_contract(mutated_contract, mutated_schema)
        except (KeyError, TypeError, ValueError):
            rejected = True
        results.append((name, rejected))
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    stage_dir = args.stage_dir.resolve()
    contract = json.loads((stage_dir / "config" / "cc_contract.json").read_text(encoding="utf-8"))
    schema = json.loads((stage_dir / "config" / "cc_result_schema.json").read_text(encoding="utf-8"))

    rows: list[tuple[str, str, str]] = []
    try:
        validate_contract(contract, schema)
        rows.append(("positive_contract_validation", "PASS", "all frozen invariants matched"))
    except (KeyError, TypeError, ValueError) as exc:
        rows.append(("positive_contract_validation", "FAIL", str(exc)))

    for name, rejected in run_negative_mutations(contract, schema):
        rows.append((name, "PASS" if rejected else "FAIL", "invalid mutation rejected" if rejected else "invalid mutation accepted"))

    required_docs = [
        "stage_plan.md",
        "cc_contract.md",
        "cc_bit_order.md",
        "cc_metric_definition.md",
        "cc_result_schema.md",
        "cc_dependency_graph.md",
        "frozen_config.csv",
    ]
    missing_docs = [name for name in required_docs if not (stage_dir / name).is_file()]
    rows.append(("required_documents", "PASS" if not missing_docs else "FAIL", ",".join(missing_docs) or "all present"))

    all_pass = all(status == "PASS" for _, status, _ in rows)
    rows.append(("stage_gate", "PASS" if all_pass else "FAIL", GATE if all_pass else "GATE_BLOCKED"))

    output = args.output or stage_dir / "results" / f"{STAGE}_check_results.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["check", "status", "detail"])
        writer.writerows(rows)

    for name, status, detail in rows:
        print(f"{status}: {name}: {detail}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
