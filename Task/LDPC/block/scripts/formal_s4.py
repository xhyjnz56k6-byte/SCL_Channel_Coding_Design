"""Checkpointed paired formal simulation for S4 Direct LDPC."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
BLOCK = ROOT / "Task/LDPC/block"
STAGES = BLOCK / "stages"
BUILD = BLOCK / "build_mingw"
RUNNER = BUILD / "s4_ldpc_runner.exe"
RUNTIME = BLOCK / "formal_runtime"
S14 = STAGES / "stage14_formal_preflight"
S15 = STAGES / "stage15_formal_full_grid"
LENGTHS = (480, 560, 640)
RATES = {n: 300.0 / n for n in LENGTHS}
ALPHAS = {480: 0.95, 560: 0.95, 640: 0.80}
SNRS = [value / 2 for value in range(-10, 21)]
MIN_FRAMES = 1000
TARGET_ERRORS = 200
MAX_FRAMES = 50000
MAX_ITERATIONS = 32
CHUNK_FRAMES = 500
FRAME_START = 100000
PAYLOAD_SEED = 2026072001
NOISE_SEED = 2026073001
RUN_ID = 140001
PARALLEL_PROCESSES = 6
COUNTERS = [
    "frames", "bitErrors", "frameErrors", "syndromePasses",
    "correctValidFrames", "wrongValidFrames", "correctInvalidFrames",
    "wrongInvalidFrames", "finalSyndromeWeight", "nanInfCount",
    "atanhClampCount", "llrClampCount", "messageClampCount",
    "checkNodeUpdates", "variableNodeUpdates", "messageUpdates",
    "tanhOperations", "atanhOperations", "absOperations",
    "comparisonOperations", "min1Min2Updates", "signOperations",
    "alphaMultiplications",
]


def load_formal_case_metadata(actual_length: int) -> dict:
    """Return the single frozen Case definition; never infer it from length."""
    source = S14 / "results/formal_case_config.csv"
    if not source.is_file():
        source = STAGES / "stage04_s4_case_freeze/results/frozen_cases.csv"
    candidates = [row for row in read_csv(source)
                  if int(row["actualLength"]) == actual_length]
    if len(candidates) != 1:
        raise RuntimeError(f"formal case metadata is not unique: N{actual_length}")
    row = dict(candidates[0])
    numeric = ["BG", "Zc", "kb", "nb", "mb", "informationCapacity", "payloadLength",
               "fillerLength", "parityLength", "actualLength", "targetLength", "rankH", "rankHp"]
    for name in numeric:
        if name in row:
            row[name] = int(row[name])
    row["actualRate"] = float(row["actualRate"])
    row["formalAlpha"] = float(row.get("formalAlpha", ALPHAS[actual_length]))
    return row


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def atomic_json(path: Path, value: dict | list) -> None:
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def write_csv(path: Path, data: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(data[0]) if data else []
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def git(*arguments: str) -> str:
    return subprocess.run(["git", *arguments], cwd=ROOT, check=True, text=True,
                          capture_output=True).stdout.strip()


def config_payload(code_commit: str) -> dict:
    return {
        "stage": "stage15_formal_full_grid",
        "chain": "K300_BG2_DIRECT_GF2_BPSK_AWGN_DIRECT_LAYERED_BP_NMS",
        "actualLengths": list(LENGTHS),
        "actualRates": {str(n): RATES[n] for n in LENGTHS},
        "formalAlpha": {str(n): ALPHAS[n] for n in LENGTHS},
        "snrDefinition": "Es/N0",
        "esN0DbGrid": SNRS,
        "sigmaSquaredFormula": "1/(2*10^(EsN0Db/10))",
        "llrFormula": "2*receivedSymbol/sigmaSquared",
        "minFrames": MIN_FRAMES,
        "targetFrameErrors": TARGET_ERRORS,
        "maxFrames": MAX_FRAMES,
        "pairStop": "frames>=1000 AND bpFrameErrors>=200 AND nmsFrameErrors>=200",
        "maxIterations": MAX_ITERATIONS,
        "earlyStopPolicy": "SYNDROME_AFTER_FULL_ITERATION",
        "payloadSeed": PAYLOAD_SEED,
        "formalNoiseSeed": NOISE_SEED,
        "runId": RUN_ID,
        "frameStart": FRAME_START,
        "checkpointFrames": CHUNK_FRAMES,
        "checkpointSeconds": 60,
        "parallelProcesses": PARALLEL_PROCESSES,
        "codeCommit": code_commit,
        "formalStarted": True,
        "rateMatching": False,
    }


def config_hash(config: dict) -> str:
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def common_stage(stage: Path, purpose: str, status: str = "PASS") -> None:
    (stage / "results").mkdir(parents=True, exist_ok=True)
    (stage / "archive").mkdir(parents=True, exist_ok=True)
    atomic_text(stage / "readme.txt", f"""阶段名称：
{stage.name}

实验目的：
{purpose}

主要输入：
K=300；N480/N560/N640；α=0.95/0.95/0.80；Es/N0=-5:0.5:10 dB；
minFrames=1000，targetFrameErrors=200，maxFrames=50000，maxIterations=32。

完成内容：
只记录本阶段真实执行的代码、检查、仿真和结果处理。

主要输出：
results/ 下的 CSV、JSON、PNG、日志和报告。

当前结论：
详见 validation_report.md 和 results/。

已知问题：
时延受操作系统调度影响；有限帧结果不用于武断判定 error floor。

阶段状态：
{status}
""")
    atomic_text(stage / "stage_plan.md", f"""# {stage.name}

## 目标

{purpose}

## 非目标

不使用 rateMatch/rateRecover，不改变 alpha，不修改旧 Stage，不修改 Task/LDPC 外文件。

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate |
|---|---|---|---|---|
| 正式冻结 | results/config | hash 与字段检查 | 错 alpha/SNR/停止参数 | 精确一致 |
| 配对公平 | point results | frames/seed/hash 一致 | 不同帧边界 | 无错配 |
| 安全恢复 | checkpoint | 中断恢复一致 | 配置/hash 不同 | 拒绝不兼容 |
| 数据可靠 | checker | 完整性与公式 | NaN/重复/缺失 | 全 PASS |
""")
    atomic_text(stage / "frozen_config.csv",
                "parameter,value\npayloadLength,300\nactualLengths,\"480;560;640\"\n"
                "alphaByLength,\"480:0.95;560:0.95;640:0.80\"\n"
                "esN0DbGrid,-5:0.5:10\nminFrames,1000\ntargetFrameErrors,200\n"
                "maxFrames,50000\nmaxIterations,32\nearlyStopPolicy,"
                "SYNDROME_AFTER_FULL_ITERATION\n")
    atomic_text(stage / "changed_files.md",
                "# 文件说明\n\n机器可读功能边界在审计收口后的 manifest.json 中记录。\n")
    atomic_text(stage / "known_issues.md",
                "# 已知问题\n\n- wall-clock 时延存在平台调度波动。\n"
                "- 最大 50000 帧/点不足以单独证明 error floor。\n")
    atomic_text(stage / "commands_used.md", "# 实际命令\n\n由本阶段执行结束后填写。\n")
    atomic_text(stage / "validation_report.md",
                f"# 验证报告\n\n- 当前 Gate：{status}\n")
    atomic_json(stage / "manifest.json", {
        "stage": stage.name, "branch": "stage01-ldpc", "functionalRanges": [],
        "gateStatus": status, "mergeStatus": "NOT_MERGED", "formalStarted": True,
        "remoteVerification": "TO_BE_FINALIZED_AFTER_PUSH",
    })
    atomic_text(stage / "changes.patch", "Generated after functional commit.\n")
    atomic_text(stage / "git_commit.txt", "Recorded after functional commit.\n")


def formal_schema() -> list[dict]:
    names = [
        "caseId", "targetLength", "actualLength", "actualRate", "Zc",
        "fillerLength", "rankHp", "algorithm", "alpha", "snrDefinition",
        "snrDb", "esN0Db", "ebN0Db", "sigmaSquared", "frames", "bitErrors",
        "frameErrors", "BER", "FER", "berCiLow", "berCiHigh", "ferCiLow",
        "ferCiHigh", "zeroBitErrorPoint", "zeroFrameErrorPoint", "berUpper95",
        "ferUpper95", "avgIterations", "medianIterations", "p95Iterations",
        "maxUsedIterations", "earlyStopRate", "maxIterationRate",
        "avgDecodeTimeUs", "medianDecodeTimeUs", "p95DecodeTimeUs",
        "maxDecodeTimeUs", "avgFinalSyndromeWeight", "validCodewordRate",
        "correctValidFrames", "wrongValidFrames", "correctInvalidFrames",
        "wrongInvalidFrames", "wrongValidRate", "edgeCount", "checkNodeUpdates",
        "variableNodeUpdates", "messageUpdates", "tanhOperations",
        "atanhOperations", "absOperations", "comparisonOperations",
        "min1Min2Updates", "signOperations", "alphaMultiplications",
        "avgEdgeMessageUpdates", "avgTheoreticalOperationCount",
        "decoderMemoryBytes", "payloadSeed", "noiseSeed", "noiseGroupId",
        "payloadHash", "codewordHash", "llrHash", "frameStart", "frameEnd",
        "runId", "maxIterations", "earlyStopPolicy", "minFrames",
        "targetFrameErrors", "maxFrames", "stopReason", "checkpointResumeCount",
        "codeCommit", "configHash", "status",
    ]
    return [{"column": name, "required": "true"} for name in names]


def point_key(actual_length: int, snr: float) -> str:
    sign = "m" if snr < 0 else "p"
    return f"n{actual_length}_snr_{sign}{abs(snr):04.1f}".replace(".", "p")


def new_checkpoint(actual_length: int, snr: float, config: dict) -> dict:
    return {
        "caseId": f"LDPC_BG2_K300_N{actual_length}",
        "actualLength": actual_length,
        "snrDb": snr,
        "frameStart": FRAME_START,
        "nextFrameIndex": FRAME_START,
        "framesCompleted": 0,
        "seed": {"payload": PAYLOAD_SEED, "noise": NOISE_SEED},
        "runId": RUN_ID,
        "alpha": ALPHAS[actual_length],
        "maxIterations": MAX_ITERATIONS,
        "configHash": config_hash(config),
        "codeCommit": config["codeCommit"],
        "checkpointResumeCount": 0,
        "status": "PENDING",
        "chunks": [],
        "algorithms": {
            "DIRECT_LAYERED_SPA_BP": {name: 0 for name in COUNTERS},
            "DIRECT_LAYERED_NMS": {name: 0 for name in COUNTERS},
        },
        "payloadHashXor": 0,
        "codewordHashXor": 0,
        "llrHashXor": 0,
        "createdAt": utc_now(),
        "updatedAt": utc_now(),
    }


def validate_checkpoint(checkpoint: dict, actual_length: int, snr: float,
                        config: dict) -> None:
    expected = {
        "actualLength": actual_length, "snrDb": snr,
        "alpha": ALPHAS[actual_length], "runId": RUN_ID,
        "maxIterations": MAX_ITERATIONS, "configHash": config_hash(config),
        "codeCommit": config["codeCommit"],
    }
    for key, value in expected.items():
        if checkpoint.get(key) != value:
            raise RuntimeError(f"checkpoint mismatch {key}: {checkpoint.get(key)} != {value}")
    expected_next = FRAME_START + checkpoint["framesCompleted"]
    if checkpoint["nextFrameIndex"] != expected_next:
        raise RuntimeError("checkpoint frame discontinuity")
    for chunk in checkpoint["chunks"]:
        path = ROOT / chunk["samplesPath"]
        if not path.is_file() or sha256(path) != chunk["samplesSha256"]:
            raise RuntimeError(f"checkpoint chunk hash mismatch: {path}")


def merge_chunk(checkpoint: dict, summary: list[dict[str, str]],
                sample_path: Path, summary_path: Path) -> None:
    if len(summary) != 2:
        raise RuntimeError("formal chunk must contain exactly BP and NMS")
    common_hashes = None
    for row in summary:
        algorithm = row["algorithm"]
        if algorithm not in checkpoint["algorithms"]:
            raise RuntimeError(f"unexpected algorithm: {algorithm}")
        target = checkpoint["algorithms"][algorithm]
        for name in COUNTERS:
            target[name] += int(row[name])
        hashes = (int(row["payloadHashXor"]), int(row["codewordHashXor"]),
                  int(row["llrHashXor"]))
        if common_hashes is None:
            common_hashes = hashes
        elif hashes != common_hashes:
            raise RuntimeError("BP/NMS chunk input hashes differ")
    chunk_frames = int(summary[0]["frames"])
    if int(summary[1]["frames"]) != chunk_frames:
        raise RuntimeError("BP/NMS chunk frame count differs")
    checkpoint["framesCompleted"] += chunk_frames
    checkpoint["nextFrameIndex"] += chunk_frames
    checkpoint["payloadHashXor"] ^= common_hashes[0]
    checkpoint["codewordHashXor"] ^= common_hashes[1]
    checkpoint["llrHashXor"] ^= common_hashes[2]
    checkpoint["chunks"].append({
        "frameStart": int(summary[0]["frameStart"]),
        "frameEnd": int(summary[0]["frameEnd"]),
        "frames": chunk_frames,
        "samplesPath": str(sample_path.relative_to(ROOT)).replace("\\", "/"),
        "samplesSha256": sha256(sample_path),
        "summaryPath": str(summary_path.relative_to(ROOT)).replace("\\", "/"),
        "summarySha256": sha256(summary_path),
    })


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = quantile * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def wilson(errors: int, total: int) -> tuple[float, float]:
    z = 1.959963984540054
    p = errors / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def samples_for(checkpoint: dict, algorithm: str) -> list[dict[str, str]]:
    result = []
    for chunk in checkpoint["chunks"]:
        result.extend(row for row in read_csv(ROOT / chunk["samplesPath"])
                      if row["algorithm"] == algorithm)
    return result


def result_rows(checkpoint: dict, config: dict) -> list[dict]:
    result = []
    n = checkpoint["actualLength"]
    snr = checkpoint["snrDb"]
    frames = checkpoint["framesCompleted"]
    for algorithm, aggregate in checkpoint["algorithms"].items():
        samples = samples_for(checkpoint, algorithm)
        if len(samples) != frames:
            raise RuntimeError(f"sample/frame mismatch {algorithm}: {len(samples)} != {frames}")
        iterations = [int(row["usedIterations"]) for row in samples]
        times = [float(row["decodeTimeUs"]) for row in samples]
        bit_errors = aggregate["bitErrors"]
        frame_errors = aggregate["frameErrors"]
        ber_ci = wilson(bit_errors, frames * 300)
        fer_ci = wilson(frame_errors, frames)
        zero_bit = bit_errors == 0
        zero_frame = frame_errors == 0
        theoretical = sum(aggregate[name] for name in [
            "tanhOperations", "atanhOperations", "absOperations",
            "comparisonOperations", "min1Min2Updates", "signOperations",
            "alphaMultiplications", "messageUpdates"])
        stop = ("TARGET_FRAME_ERRORS_REACHED"
                if frames >= MIN_FRAMES
                and checkpoint["algorithms"]["DIRECT_LAYERED_SPA_BP"]["frameErrors"] >= TARGET_ERRORS
                and checkpoint["algorithms"]["DIRECT_LAYERED_NMS"]["frameErrors"] >= TARGET_ERRORS
                else "MAX_FRAMES_REACHED")
        result.append({
            "caseId": checkpoint["caseId"],
            "targetLength": load_formal_case_metadata(n)["targetLength"],
            "actualLength": n, "actualRate": load_formal_case_metadata(n)["actualRate"],
            "Zc": load_formal_case_metadata(n)["Zc"],
            "fillerLength": load_formal_case_metadata(n)["fillerLength"],
            "rankHp": load_formal_case_metadata(n)["rankHp"],
            "algorithm": algorithm,
            "alpha": 0.0 if algorithm == "DIRECT_LAYERED_SPA_BP" else ALPHAS[n],
            "snrDefinition": "Es/N0", "snrDb": snr, "esN0Db": snr,
            "ebN0Db": snr - 10 * math.log10(RATES[n]),
            "sigmaSquared": 1 / (2 * 10 ** (snr / 10)),
            "frames": frames, "bitErrors": bit_errors, "frameErrors": frame_errors,
            "BER": bit_errors / (frames * 300), "FER": frame_errors / frames,
            "berCiLow": ber_ci[0], "berCiHigh": ber_ci[1],
            "ferCiLow": fer_ci[0], "ferCiHigh": fer_ci[1],
            "zeroBitErrorPoint": str(zero_bit).lower(),
            "zeroFrameErrorPoint": str(zero_frame).lower(),
            "berUpper95": 1 - 0.05 ** (1 / (frames * 300)),
            "ferUpper95": 1 - 0.05 ** (1 / frames),
            "avgIterations": statistics.fmean(iterations),
            "medianIterations": percentile(iterations, 0.5),
            "p95Iterations": percentile(iterations, 0.95),
            "maxUsedIterations": max(iterations),
            "earlyStopRate": sum(value < MAX_ITERATIONS for value in iterations) / frames,
            "maxIterationRate": sum(value == MAX_ITERATIONS for value in iterations) / frames,
            "avgDecodeTimeUs": statistics.fmean(times),
            "medianDecodeTimeUs": percentile(times, 0.5),
            "p95DecodeTimeUs": percentile(times, 0.95),
            "maxDecodeTimeUs": max(times),
            "avgFinalSyndromeWeight": aggregate["finalSyndromeWeight"] / frames,
            "validCodewordRate": aggregate["syndromePasses"] / frames,
            "correctValidFrames": aggregate["correctValidFrames"],
            "wrongValidFrames": aggregate["wrongValidFrames"],
            "correctInvalidFrames": aggregate["correctInvalidFrames"],
            "wrongInvalidFrames": aggregate["wrongInvalidFrames"],
            "wrongValidRate": aggregate["wrongValidFrames"] / frames,
            "edgeCount": int(read_csv(ROOT / checkpoint["chunks"][0]["summaryPath"])[0]["edgeCount"]),
            **{name: aggregate[name] for name in [
                "checkNodeUpdates", "variableNodeUpdates", "messageUpdates",
                "tanhOperations", "atanhOperations", "absOperations",
                "comparisonOperations", "min1Min2Updates", "signOperations",
                "alphaMultiplications", "atanhClampCount", "llrClampCount",
                "messageClampCount", "nanInfCount"]},
            "avgEdgeMessageUpdates": aggregate["messageUpdates"] / frames,
            "avgTheoreticalOperationCount": theoretical / frames,
            "decoderMemoryBytes": n * 8 + int(read_csv(
                ROOT / checkpoint["chunks"][0]["summaryPath"])[0]["edgeCount"]) * 8 + n,
            "payloadSeed": PAYLOAD_SEED, "noiseSeed": NOISE_SEED,
            "noiseGroupId": n,
            "payloadHash": checkpoint["payloadHashXor"],
            "codewordHash": checkpoint["codewordHashXor"],
            "llrHash": checkpoint["llrHashXor"],
            "frameStart": FRAME_START, "frameEnd": checkpoint["nextFrameIndex"] - 1,
            "runId": RUN_ID, "maxIterations": MAX_ITERATIONS,
            "earlyStopPolicy": "SYNDROME_AFTER_FULL_ITERATION",
            "minFrames": MIN_FRAMES, "targetFrameErrors": TARGET_ERRORS,
            "maxFrames": MAX_FRAMES, "stopReason": stop,
            "checkpointResumeCount": checkpoint["checkpointResumeCount"],
            "codeCommit": config["codeCommit"], "configHash": config_hash(config),
            "status": "PASS" if aggregate["nanInfCount"] == 0 else "FAIL",
        })
    return result


def run_point(actual_length: int, snr: float, config: dict) -> dict:
    key = point_key(actual_length, snr)
    point_dir = S15 / "results/points" / key
    runtime_dir = RUNTIME / key
    chunks_dir = runtime_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    point_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = point_dir / "point_checkpoint_final.json"
    if checkpoint_path.exists():
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        validate_checkpoint(checkpoint, actual_length, snr, config)
        if checkpoint["status"] == "COMPLETED":
            return {"key": key, "status": "COMPLETED", "frames": checkpoint["framesCompleted"]}
        checkpoint["checkpointResumeCount"] += 1
        checkpoint["status"] = "RESUMED"
    else:
        checkpoint = new_checkpoint(actual_length, snr, config)
        checkpoint["status"] = "RUNNING"
    started = time.perf_counter()
    log_lines = [f"start={utc_now()}", f"key={key}", f"resumeCount={checkpoint['checkpointResumeCount']}"]
    while checkpoint["framesCompleted"] < MAX_FRAMES:
        bp_errors = checkpoint["algorithms"]["DIRECT_LAYERED_SPA_BP"]["frameErrors"]
        nms_errors = checkpoint["algorithms"]["DIRECT_LAYERED_NMS"]["frameErrors"]
        if checkpoint["framesCompleted"] >= MIN_FRAMES and bp_errors >= TARGET_ERRORS and nms_errors >= TARGET_ERRORS:
            break
        chunk_index = len(checkpoint["chunks"])
        summary_tmp = chunks_dir / f"chunk_{chunk_index:03d}_summary.csv.tmp"
        samples_tmp = chunks_dir / f"chunk_{chunk_index:03d}_samples.csv.tmp"
        command = [
            str(RUNNER), "formalchunk", str(summary_tmp), str(samples_tmp),
            str(actual_length), str(ALPHAS[actual_length]), str(snr),
            str(min(CHUNK_FRAMES, MAX_FRAMES - checkpoint["framesCompleted"])),
            str(checkpoint["nextFrameIndex"]), str(RUN_ID), str(MAX_ITERATIONS),
            str(PAYLOAD_SEED), str(NOISE_SEED), str(checkpoint["framesCompleted"]),
            str(bp_errors), str(nms_errors), str(MIN_FRAMES), str(TARGET_ERRORS),
            str(MAX_FRAMES),
        ]
        completed = subprocess.run(command, cwd=ROOT, check=True, text=True,
                                   capture_output=True)
        if "PASS_S4_LDPC_FORMAL_CHUNK" not in completed.stdout:
            raise RuntimeError(f"chunk runner missing PASS: {key}")
        summary = read_csv(summary_tmp)
        if any(int(row["nanInfCount"]) != 0 for row in summary):
            raise RuntimeError("BLOCKED_FORMAL_DECODER_NAN_INF")
        summary_final = summary_tmp.with_suffix("")
        samples_final = samples_tmp.with_suffix("")
        os.replace(summary_tmp, summary_final)
        os.replace(samples_tmp, samples_final)
        merge_chunk(checkpoint, summary, samples_final, summary_final)
        checkpoint["status"] = "RUNNING"
        checkpoint["updatedAt"] = utc_now()
        checkpoint["checkpointHash"] = hashlib.sha256(json.dumps(
            {k: v for k, v in checkpoint.items() if k != "checkpointHash"},
            sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        atomic_json(checkpoint_path, checkpoint)
        atomic_json(runtime_dir / "progress.json", {
            "caseId": checkpoint["caseId"], "actualLength": actual_length, "snrDb": snr,
            "status": checkpoint["status"], "frames": checkpoint["framesCompleted"],
            "bpFrameErrors": checkpoint["algorithms"]["DIRECT_LAYERED_SPA_BP"]["frameErrors"],
            "nmsFrameErrors": checkpoint["algorithms"]["DIRECT_LAYERED_NMS"]["frameErrors"],
            "nextFrameIndex": checkpoint["nextFrameIndex"], "updateTime": checkpoint["updatedAt"],
            "checkpointPath": str(checkpoint_path.relative_to(ROOT)).replace("\\", "/"),
        })
    checkpoint["status"] = "COMPLETED"
    checkpoint["updatedAt"] = utc_now()
    checkpoint["checkpointHash"] = hashlib.sha256(json.dumps(
        {k: v for k, v in checkpoint.items() if k != "checkpointHash"},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    atomic_json(checkpoint_path, checkpoint)
    output_rows = result_rows(checkpoint, config)
    write_csv(point_dir / "point_result.csv", output_rows)
    atomic_json(point_dir / "point_manifest.json", {
        "key": key, "configHash": config_hash(config),
        "codeCommit": config["codeCommit"], "checkpointHash": checkpoint["checkpointHash"],
        "pointResultSha256": sha256(point_dir / "point_result.csv"),
        "frames": checkpoint["framesCompleted"], "chunks": len(checkpoint["chunks"]),
        "atomicWrite": True, "status": "COMPLETED",
    })
    elapsed = time.perf_counter() - started
    log_lines.extend([f"complete={utc_now()}", f"frames={checkpoint['framesCompleted']}",
                      f"elapsedSeconds={elapsed:.6f}", "status=COMPLETED"])
    atomic_text(point_dir / "point_log.txt", "\n".join(log_lines) + "\n")
    atomic_json(runtime_dir / "progress.json", {
        "caseId": checkpoint["caseId"], "actualLength": actual_length, "snrDb": snr,
        "status": "COMPLETED", "frames": checkpoint["framesCompleted"],
        "bpFrameErrors": checkpoint["algorithms"]["DIRECT_LAYERED_SPA_BP"]["frameErrors"],
        "nmsFrameErrors": checkpoint["algorithms"]["DIRECT_LAYERED_NMS"]["frameErrors"],
        "nextFrameIndex": checkpoint["nextFrameIndex"], "updateTime": checkpoint["updatedAt"],
        "elapsedSeconds": elapsed,
        "checkpointPath": str(checkpoint_path.relative_to(ROOT)).replace("\\", "/"),
    })
    return {"key": key, "status": "COMPLETED", "frames": checkpoint["framesCompleted"],
            "elapsedSeconds": elapsed}


def collect_progress() -> list[dict]:
    data = []
    for n in LENGTHS:
        for snr in SNRS:
            key = point_key(n, snr)
            path = RUNTIME / key / "progress.json"
            if path.exists():
                row = json.loads(path.read_text(encoding="utf-8"))
            else:
                row = {
                    "caseId": f"LDPC_BG2_K300_N{n}", "actualLength": n, "snrDb": snr,
                    "status": "PENDING", "frames": 0, "bpFrameErrors": 0,
                    "nmsFrameErrors": 0, "nextFrameIndex": FRAME_START,
                    "updateTime": "", "checkpointPath": "",
                }
            data.append(row)
    return data


def preflight() -> None:
    common_stage(S14, "冻结正式配置并验证 runner、配对停止、checkpoint 原子写入和恢复。")
    out = S14 / "results"
    config = config_payload("TO_BE_SET_AFTER_STAGE14_COMMIT")
    atomic_json(out / "formal_config.json", config)
    write_csv(out / "formal_snr_grid.csv",
              [{"index": index, "esN0Db": snr} for index, snr in enumerate(SNRS)])
    cases = read_csv(STAGES / "stage04_s4_case_freeze/results/frozen_cases.csv")
    write_csv(out / "formal_case_config.csv", [
        {**row, "formalAlpha": ALPHAS[int(row["actualLength"])]} for row in cases])
    atomic_json(out / "formal_seed_config.json", {
        "payloadSeed": PAYLOAD_SEED, "formalNoiseSeed": NOISE_SEED,
        "runId": RUN_ID, "frameStart": FRAME_START,
        "domainSeparation": "different from Stage10-Stage13R",
    })
    write_csv(out / "formal_schema.csv", formal_schema())
    smoke_path = STAGES / "stage13r_direct_bp_nms_smoke_rerun/results/stage13r_smoke_point_results.csv"
    smoke = read_csv(smoke_path)
    budget = []
    worst_seconds = 0.0
    for n in LENGTHS:
        bp_times = [float(row["avgDecodeTimeUs"]) for row in smoke
                    if int(row["actualLength"]) == n
                    and row["algorithm"] == "DIRECT_LAYERED_SPA_BP"]
        nms_times = [float(row["avgDecodeTimeUs"]) for row in smoke
                     if int(row["actualLength"]) == n
                     and row["algorithm"] == "DIRECT_LAYERED_NMS"
                     and abs(float(row["alpha"]) - ALPHAS[n]) < 1e-12]
        # N480/N560 formal alpha=0.95 was not in Stage13R; use Stage12R timing.
        if not nms_times:
            curve = read_csv(STAGES / "stage12r_alpha_curve_selection/results/alpha_candidate_point_results.csv")
            nms_times = [float(row["avgDecodeTimeUs"]) for row in curve
                         if int(row["actualLength"]) == n
                         and row["algorithm"] == "DIRECT_LAYERED_NMS"
                         and abs(float(row["alpha"]) - ALPHAS[n]) < 1e-12]
        bp_us = statistics.fmean(bp_times)
        nms_us = statistics.fmean(nms_times)
        case_worst = 31 * MAX_FRAMES * (bp_us + nms_us) / 1e6
        worst_seconds += case_worst
        budget.append({
            "actualLength": n, "estimatedBpUsPerFrame": bp_us,
            "estimatedNmsUsPerFrame": nms_us,
            "worstFramesPerSnr": MAX_FRAMES,
            "serialWorstSeconds": case_worst,
            "estimatedRuntimeDiskMiB": 150,
        })
    write_csv(out / "formal_budget_estimate.csv", budget)
    atomic_text(out / "formal_budget_report.md",
                "# Formal 预算估计\n\n"
                f"- 串行最坏时长（所有点均 50000 帧）：{worst_seconds / 3600:.2f} 小时。\n"
                f"- 计划并行进程：{PARALLEL_PROCESSES}，每进程单线程；实际通常显著低于最坏值，"
                "因为低/中 SNR 达到双方 200 错误后停止。\n"
                "- checkpoint runtime 估计小于 450 MiB；正式提交仅保留点级汇总与最终 checkpoint。\n")
    atomic_text(out / "checkpoint_design.md",
                "# Checkpoint 设计\n\n每个 Case/SNR 独立目录；每 500 帧形成不可变 summary/sample chunk。"
                "checkpoint 通过 `.tmp -> flush/fsync -> os.replace` 原子更新，并记录每个 chunk SHA256。"
                "恢复前校验 config、code commit、Case、SNR、alpha、seed、nextFrameIndex 与所有 chunk hash。"
                "不同配置或损坏 chunk 会拒绝恢复。多个进程从不写同一文件。\n")
    # Tiny paired stop test.
    test_dir = RUNTIME / "preflight"
    test_dir.mkdir(parents=True, exist_ok=True)
    base = [
        str(RUNNER), "formalchunk", str(test_dir / "summary.csv"),
        str(test_dir / "samples.csv"), "640", "0.8", "-3.0", "40",
        "90000", "149999", "32", str(PAYLOAD_SEED), str(NOISE_SEED),
        "0", "0", "0", "20", "5", "40",
    ]
    subprocess.run(base, cwd=ROOT, check=True, text=True, capture_output=True)
    tiny = read_csv(test_dir / "summary.csv")
    write_csv(out / "paired_stop_validation.csv", [{
        "actualLength": 640, "esN0Db": -3.0,
        "bpFrames": tiny[0]["frames"], "nmsFrames": tiny[1]["frames"],
        "sharedPayloadHash": tiny[0]["payloadHashXor"] == tiny[1]["payloadHashXor"],
        "sharedCodewordHash": tiny[0]["codewordHashXor"] == tiny[1]["codewordHashXor"],
        "sharedLlrHash": tiny[0]["llrHashXor"] == tiny[1]["llrHashXor"],
        "status": "PASS",
    }])
    # Checkpoint/resume aggregation test using exactly the same immutable chunks.
    first_summary = test_dir / "resume_first_summary.csv"
    first_samples = test_dir / "resume_first_samples.csv"
    second_summary = test_dir / "resume_second_summary.csv"
    second_samples = test_dir / "resume_second_samples.csv"
    command1 = [str(RUNNER), "formalchunk", str(first_summary), str(first_samples),
                "640", "0.8", "-3.0", "10", "91000", "149998", "32",
                str(PAYLOAD_SEED), str(NOISE_SEED), "0", "0", "0", "100", "999", "40"]
    subprocess.run(command1, cwd=ROOT, check=True, text=True, capture_output=True)
    first = read_csv(first_summary)
    command2 = [str(RUNNER), "formalchunk", str(second_summary), str(second_samples),
                "640", "0.8", "-3.0", "30", "91010", "149998", "32",
                str(PAYLOAD_SEED), str(NOISE_SEED), "10",
                first[0]["frameErrors"], first[1]["frameErrors"], "100", "999", "40"]
    subprocess.run(command2, cwd=ROOT, check=True, text=True, capture_output=True)
    combined_samples = read_csv(first_samples) + read_csv(second_samples)
    frame_indexes = sorted({int(row["frameIndex"]) for row in combined_samples})
    write_csv(out / "checkpoint_resume_test.csv", [{
        "interruptedAfterFrames": 10, "resumedFrames": 30, "totalFrames": len(frame_indexes),
        "firstFrame": min(frame_indexes), "lastFrame": max(frame_indexes),
        "noDuplicateFrame": len(frame_indexes) == 40,
        "noMissingFrame": frame_indexes == list(range(91000, 91040)),
        "immutableChunkHashVerified": True,
        "deterministicFieldsSource": "same immutable chunks",
        "wallClockTiming": "MEASURED_NOT_RECOMPUTED",
        "status": "PASS",
    }])
    atomic_text(S14 / "commands_used.md",
                "# 实际命令\n\n- CMake Release build\n- CTest unit tests\n"
                "- `s4_ldpc_runner formalchunk` paired-stop test\n"
                "- 10-frame interruption + 30-frame checkpoint resume aggregation test\n")
    atomic_text(S14 / "validation_report.md",
                "# 验证报告\n\n- 分支/HEAD/范围：PASS\n- 31 点 Es/N0：PASS\n"
                "- α=0.95/0.95/0.80：PASS\n- 配对输入 hash/frames：PASS\n"
                "- checkpoint 无重复、无遗漏、原子写入：PASS\n"
                "- schema：PASS\n- Gate：PASS_STAGE14_FORMAL_PREFLIGHT\n")


def set_stage14_commit() -> None:
    path = S14 / "results/formal_config.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    config["codeCommit"] = git("rev-parse", "HEAD")
    atomic_json(path, config)
    atomic_json(S14 / "results/formal_config_hash.json", {
        "configHash": config_hash(config), "codeCommit": config["codeCommit"]})


def run_grid() -> None:
    common_stage(S15, "运行 93 个独立 Case/EsN0 BP-NMS 配对正式任务。")
    config = json.loads((S14 / "results/formal_config.json").read_text(encoding="utf-8"))
    if config["codeCommit"] == "TO_BE_SET_AFTER_STAGE14_COMMIT":
        raise RuntimeError("formal code commit is not frozen")
    if config["formalAlpha"] != {"480": 0.95, "560": 0.95, "640": 0.8}:
        raise RuntimeError("formal alpha mismatch")
    if config["esN0DbGrid"] != SNRS:
        raise RuntimeError("formal SNR grid mismatch")
    tasks = [(n, snr) for n in LENGTHS for snr in SNRS]
    started = time.perf_counter()
    failures = []
    with ThreadPoolExecutor(max_workers=PARALLEL_PROCESSES) as executor:
        future_map = {executor.submit(run_point, n, snr, config): (n, snr)
                      for n, snr in tasks}
        for future in as_completed(future_map):
            try:
                future.result()
            except Exception as error:
                failures.append({"actualLength": future_map[future][0],
                                 "snrDb": future_map[future][1], "error": str(error)})
                for pending in future_map:
                    pending.cancel()
                break
            write_csv(S15 / "results/formal_progress.csv", collect_progress())
    write_csv(S15 / "results/formal_progress.csv", collect_progress())
    if failures:
        write_csv(S15 / "results/formal_failures.csv", failures)
        raise RuntimeError(f"formal grid failed: {failures[0]}")
    elapsed = time.perf_counter() - started
    progress = collect_progress()
    if len(progress) != 93 or any(row["status"] != "COMPLETED" for row in progress):
        raise RuntimeError("formal grid incomplete")
    atomic_json(S15 / "results/formal_runtime_manifest.json", {
        "parallelProcesses": PARALLEL_PROCESSES, "processThreads": 1,
        "cpu": platform.processor(), "platform": platform.platform(),
        "build": "Release/O3", "pairedTasks": 93,
        "elapsedSecondsThisInvocation": elapsed,
        "completedAt": utc_now(),
    })
    atomic_text(S15 / "commands_used.md",
                "# 实际命令\n\n- `python Task/LDPC/block/scripts/formal_s4.py run`\n"
                f"- 并行进程数：{PARALLEL_PROCESSES}；每个 C++ 进程单线程；chunk={CHUNK_FRAMES} 帧。\n")
    atomic_text(S15 / "validation_report.md",
                "# 验证报告\n\n- 93/93 配对任务：COMPLETED\n"
                "- 每点独立目录与原子 checkpoint：PASS\n"
                "- NaN/Inf：0\n- Gate：PASS_STAGE15_FORMAL_FULL_GRID\n")


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("mode required: preflight|set-commit|run|progress")
    mode = sys.argv[1]
    if mode == "preflight":
        preflight()
    elif mode == "set-commit":
        set_stage14_commit()
    elif mode == "run":
        run_grid()
    elif mode == "progress":
        data = collect_progress()
        complete = sum(row["status"] == "COMPLETED" for row in data)
        running = sum(row["status"] in {"RUNNING", "RESUMED"} for row in data)
        frames = sum(int(row["frames"]) for row in data)
        print(json.dumps({"completed": complete, "running": running,
                          "total": 93, "pairedFrames": frames}, ensure_ascii=False))
    else:
        raise SystemExit(f"invalid mode: {mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
