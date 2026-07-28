#!/usr/bin/env python3
"""Prepare the frozen common waveform-SNR grid and static audit skeleton."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path

PREFIX = "stage08_multipath_formal_common_snr"
CASES = [
    ("K200_S15", "分块200", 200, 285),
    ("K200_M255K207", "255整块200", 200, 248),
    ("K200_M511K421", "421整块200", 200, 290),
    ("K200_M511K385", "385整块200", 200, 326),
    ("K300_S15", "分块300", 300, 420),
    ("K300_M255K207", "255双块300", 300, 396),
    ("K300_M511K421", "421整块300", 300, 390),
    ("K300_M511K385", "385整块300", 300, 426),
]


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    repo = stage.parents[5]
    for name in ("configs", "results", "plots", "logs", "checkpoints", "manifests"):
        (stage / name).mkdir(exist_ok=True)
    head = git(repo, "rev-parse", "HEAD")
    model_path = stage.parent / "stage07_multipath_validation" / "stage07_multipath_validation_frozen_model.json"
    model = json.loads(model_path.read_text(encoding="utf-8"))
    rows = []
    for case_id, _legend, payload, encoded in CASES:
        rate = payload / encoded
        for index in range(37):
            waveform_snr_db = index * 0.5
            snr_linear = 10.0 ** (waveform_snr_db / 10.0)
            sigma2 = 1.0 / snr_linear
            derived_ebn0_db = waveform_snr_db - 10.0 * math.log10(2.0 * rate)
            sigma2_from_ebn0 = 1.0 / (2.0 * rate * 10.0 ** (derived_ebn0_db / 10.0))
            if abs(sigma2 - sigma2_from_ebn0) > 1e-14:
                raise RuntimeError("sigma2 identity failed")
            rows.append({
                "caseId": case_id,
                "waveformSnrIndex": index,
                "waveformSnrDb": f"{waveform_snr_db:.1f}",
                "snrLinear": f"{snr_linear:.17g}",
                "actualRate": f"{rate:.17g}",
                "derivedEbn0Db": f"{derived_ebn0_db:.17g}",
                "sigma2": f"{sigma2:.17g}",
                "gridType": "BASE_0P5DB",
            })
    grid = stage / f"{PREFIX}_frozen_grid.csv"
    with grid.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    config = {
        "stageId": PREFIX,
        "baseHeadAtStart": head,
        "gridDefinition": "waveformSnrDb=0:0.5:18 dB",
        "gridType": "BASE_0P5DB",
        "pointCount": 296,
        "pointsPerCase": 37,
        "masterSeed": 8080808,
        "minFrames": 1000,
        "targetFrameErrors": 200,
        "maxFrames": 50000,
        "checkpointIntervalFrames": 1000,
        "shardCount": 2,
        "channelModelSource": "../stage07_multipath_validation/stage07_multipath_validation_frozen_model.json",
        "channelModelId": model["channelModelId"],
        "normalizedImpulseResponse": model["normalizedImpulseResponse"],
        "sigma2FormulaPrimary": "10^(-waveformSnrDb/10)",
        "derivedEbn0DbFormula": "waveformSnrDb-10*log10(2*R)",
        "sigma2FormulaEquivalence": "1/(2*R*10^(derivedEbn0Db/10))",
        "legacyStage08Label": "LEGACY_WIDE_GRID_FORMAL",
        "mergeStatus": "NOT_MERGED",
    }
    config_path = stage / f"{PREFIX}_config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (stage / "configs" / config_path.name).write_text(config_path.read_text(encoding="utf-8"), encoding="utf-8")
    acceptance = stage / f"{PREFIX}_acceptance_matrix.csv"
    acceptance.write_text(
        "requirement,implementation,positiveTest,negativeTest,gate\n"
        "common waveform SNR grid,runner frozen grid,296 rows and 37 points per case,missing duplicate or extra point blocked,PASS_STAGE08_COMMON_SNR_RESULTS_CHECK\n"
        "sigma2 identity,runner and checker,recompute both formulas,nonfinite or mismatch blocked,PASS_STAGE08_COMMON_SNR_RESULTS_CHECK\n"
        "plot evidence,matplotlib script,8 PNG plus figure-data and manifests,forbidden format or missing point blocked,PASS_STAGE08_COMMON_SNR_PLOT_CHECK\n"
        "fair comparison,ranking and crossing scripts,same payload and same SNR only,cross-SNR ranking blocked,PASS_STAGE08_MULTIPATH_COMMON_SNR_COMPARISON\n",
        encoding="utf-8",
    )
    (stage / f"{PREFIX}_stage_plan.md").write_text(
        f"# {PREFIX}\n\n"
        "目标：在统一接收波形 SNR 横坐标下完成 BCH S2 固定多径正式补充实验。\n\n"
        "非目标：不修改 Stage07 多径模型，不覆盖旧 Stage08 宽网格结果，不修改 CC/LDPC/Common。\n\n"
        "范围：仅新增 Task/BCH/simulation/stages/S2/stage08_multipath_formal_common_snr。\n\n"
        "Gate：self-test、checkpoint/resume、shard/merge、results checker、plot checker、audit 全部 PASS 后提交并 push。\n",
        encoding="utf-8",
    )
    (stage / f"{PREFIX}_commands_used.md").write_text(
        "# Commands Used\n\n"
        "- git safety checks\n"
        "- python stage08_multipath_formal_common_snr_prepare.py\n"
        "- cmake -S cpp -B build -DCMAKE_BUILD_TYPE=Release\n"
        "- cmake --build build --config Release\n"
        "- runner --self-test frozen_grid\n"
        "- runner shard 0/2 and shard 1/2\n"
        "- python process/check/plot/plot_check/finalize scripts\n"
        "- git diff --check; git commit; git push origin stage07-08-bch-s2-multipath\n",
        encoding="utf-8",
    )
    print(f"PASS_STAGE08_COMMON_SNR_PREPARE rows={len(rows)} gridSha256={sha(grid)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
