#!/usr/bin/env python3
"""Independent business checker for the S2-07 redesign artifacts."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value: bool, gate: str) -> None:
    if not value:
        raise RuntimeError(gate)


def main() -> int:
    repo = Path(__file__).resolve().parents[4]
    stages = repo / "Task/BCH/simulation/stages"
    names = {
        "a": "s2_07a_block_burst_correction_boundary",
        "b": "s2_07b_segmented_boundary_heatmap",
        "c": "s2_07c_random_burst_performance",
        "d": "s2_07d_burst_interleaving",
    }
    data = {
        key: rows(stages / name / "formal_summary.csv")
        for key, name in names.items()
    }
    require(len(data["a"]) == 45, "FAIL_BCH_S2_07A_ROW_COUNT")
    require(len(data["b"]) == 900, "FAIL_BCH_S2_07B_HEATMAP_GRID")
    require(len(data["c"]) == 185, "FAIL_BCH_S2_07C_GRID")
    require(len(data["d"]) == 370, "FAIL_BCH_S2_07D_GRID")
    for key, values in data.items():
        require(all(int(row["processedFrames"]) > 0 for row in values),
                f"FAIL_BCH_S2_07{key.upper()}_EMPTY")
        require(all(math.isfinite(float(row["FER"])) for row in values),
                f"FAIL_BCH_S2_07{key.upper()}_NONFINITE")
    guaranteed_a = [
        row for row in data["a"]
        if int(row["burstLength"]) <= int(row["correctionCapabilityT"])
    ]
    require(all(float(row["FER"]) == 0.0 for row in guaranteed_a),
            "FAIL_BCH_S2_07A_GUARANTEED_REGION")
    cross = [
        row for row in data["b"]
        if row["burstLength"] == "2"
        and row["relativeStartInSubblock"] == "14"
    ]
    require(len(cross) == 2 and all(float(row["FER"]) == 0.0 for row in cross),
            "FAIL_BCH_S2_07B_CROSS_BOUNDARY")
    require(all(row["errorWeightConserved"] == "true" for row in data["d"]),
            "FAIL_BCH_S2_07D_ERROR_WEIGHT_CONSERVATION")
    manifest_path = stages / "s2_07_burst_redesign_audit/plot_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest["figureCount"] >= 12,
            "FAIL_BCH_S2_07_PLOT_COUNT")
    for item in manifest["figures"]:
        image = manifest_path.parent / "figures" / item["filename"]
        figure_data = manifest_path.parent / "figures" / item["figureData"]
        require(image.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n",
                "FAIL_BCH_S2_07_NON_PNG")
        require(sha(image) == item["pngSha256"],
                "FAIL_BCH_S2_07_PNG_HASH")
        require(sha(figure_data) == item["figureDataSha256"],
                "FAIL_BCH_S2_07_FIGURE_DATA_HASH")
        require(item["xLabel"] != "波形信噪比 SNR（dB）",
                "FAIL_BCH_S2_07_OLD_SNR_LABEL")
    part_a = [
        item for item in manifest["figures"]
        if "_redesigned" in item["filename"]
    ]
    require(len(part_a) == 4 and all(
        item["xLabel"] == "SNR（dB）" and item["yLabel"] == "误帧率 FER"
        and item["yScale"] == "log" for item in part_a
    ), "FAIL_BCH_S2_CHANNEL_FER_PLOT_DISTINGUISHABILITY")
    print("PASS_BCH_S2_CHANNEL_FER_PLOT_DISTINGUISHABILITY")
    print("PASS_BCH_S2_BURST_REDESIGN_CTEST")
    print("PASS_BCH_S2_07A_BLOCK_BURST_CORRECTION_BOUNDARY")
    print("PASS_BCH_S2_07B_SEGMENTED_BOUNDARY_HEATMAP")
    print("PASS_BCH_S2_07C_RANDOM_BURST_PERFORMANCE")
    print("PASS_BCH_S2_07D_BURST_INTERLEAVING")
    print("PASS_BCH_S2_07_BURST_PLOT_AUDIT")
    print("PASS_BCH_S2_07_BURST_STRUCTURE_AND_INTERLEAVING")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
