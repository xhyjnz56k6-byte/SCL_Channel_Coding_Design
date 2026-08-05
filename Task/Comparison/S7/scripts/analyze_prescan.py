from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path


WEIGHTS = {"meanFer": 0.40, "worstPositionFer": 0.30, "bufferFraction": 0.15, "deinterleaveCost": 0.15}


def norm(value: float, values: list[float]) -> float:
    lo, hi = min(values), max(values)
    return 0.0 if hi == lo else (value - lo) / (hi - lo)


def dominates(a: dict, b: dict) -> bool:
    keys = ("meanFer", "worstPositionFer", "bufferFraction", "deinterleaveTimeMeanNs")
    return all(a[k] <= b[k] for k in keys) and any(a[k] < b[k] for k in keys)


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: analyze_prescan.py PRESCAN_RAW_CSV OUTPUT_DIRECTORY")
    raw_path = Path(sys.argv[1]).resolve()
    output_dir = Path(sys.argv[2]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    with raw_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError("empty prescan CSV")

    numeric = ["EsN0Db", "sigmaSquared", "burstRatioRequested", "burstRatioActual", "BER", "FER",
               "interleaveTimeMeanNs", "deinterleaveTimeMeanNs", "decodeTimeMeanNs"]
    for row in rows:
        for key in numeric:
            value = float(row[key])
            if not math.isfinite(value):
                raise RuntimeError(f"NaN/Inf in {key}")
        if int(row["framesProcessed"]) <= 0:
            raise RuntimeError("non-positive frame count")
        if abs(float(row["BER"]) - int(row["bitErrors"]) / int(row["totalBits"])) > 1e-15:
            raise RuntimeError("BER/count mismatch")
        if abs(float(row["FER"]) - int(row["frameErrors"]) / int(row["framesProcessed"])) > 1e-15:
            raise RuntimeError("FER/count mismatch")

    fairness = defaultdict(list)
    for row in rows:
        key = (row["scheme"], row["EsN0Db"], row["burstRatioRequested"], row["burstPositionType"])
        fairness[key].append(row)
    for key, group in fairness.items():
        for field in ("framesProcessed", "payloadChecksum", "noiseChecksum", "burstStartChecksum", "frameSequenceHash"):
            if len({item[field] for item in group}) != 1:
                raise RuntimeError(f"fairness mismatch {key} field={field}")

    group_spreads = {}
    for key, group in fairness.items():
        fers = [float(item["FER"]) for item in group]
        group_spreads[key] = max(fers) - min(fers)
    informative_keys = {key for key, spread in group_spreads.items() if spread > 0.0}
    if not informative_keys:
        raise RuntimeError("no informative comparison group; parameter ranking would be meaningless")

    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["scheme"], row["method"], int(row["parameter"]))].append(row)
    metrics = []
    for (scheme, method, parameter), group in grouped.items():
        informative = [item for item in group if (item["scheme"], item["EsN0Db"], item["burstRatioRequested"], item["burstPositionType"]) in informative_keys]
        if not informative:
            informative = group
        position_values = defaultdict(list)
        for item in informative:
            position_values[item["burstPositionType"]].append(float(item["FER"]))
        position_means = {key: sum(values) / len(values) for key, values in position_values.items()}
        encoded = 285 if scheme == "BCH" else 612
        metrics.append({
            "scheme": scheme,
            "method": method,
            "parameter": parameter,
            "fairnessGroupId": group[0]["fairnessGroupId"],
            "spanBits": int(group[0]["spanBits"]),
            "bufferBits": int(group[0]["bufferBits"]),
            "meanFer": sum(float(item["FER"]) for item in informative) / len(informative),
            "overallMeanFer": sum(float(item["FER"]) for item in group) / len(group),
            "worstPositionFer": max(position_means.values()),
            "worstPosition": max(position_means, key=position_means.get),
            "bufferFraction": int(group[0]["bufferBits"]) / encoded,
            "deinterleaveTimeMeanNs": sum(float(item["deinterleaveTimeMeanNs"]) for item in group) / len(group),
            "decodeTimeMeanNs": sum(float(item["decodeTimeMeanNs"]) for item in group) / len(group),
        })

    ranked = []
    for scheme in ("BCH", "CC"):
        items = [item for item in metrics if item["scheme"] == scheme]
        columns = {
            "meanFer": [item["meanFer"] for item in items],
            "worstPositionFer": [item["worstPositionFer"] for item in items],
            "bufferFraction": [item["bufferFraction"] for item in items],
            "deinterleaveCost": [item["deinterleaveTimeMeanNs"] for item in items],
        }
        for item in items:
            item["score"] = (
                WEIGHTS["meanFer"] * norm(item["meanFer"], columns["meanFer"])
                + WEIGHTS["worstPositionFer"] * norm(item["worstPositionFer"], columns["worstPositionFer"])
                + WEIGHTS["bufferFraction"] * norm(item["bufferFraction"], columns["bufferFraction"])
                + WEIGHTS["deinterleaveCost"] * norm(item["deinterleaveTimeMeanNs"], columns["deinterleaveCost"])
            )
            item["paretoOptimal"] = not any(dominates(other, item) for other in items if other is not item)
        items.sort(key=lambda item: (item["score"], item["method"], item["parameter"]))
        for rank, item in enumerate(items, 1):
            item["rank"] = rank
            ranked.append(item)

    ranking_path = output_dir / "candidate_ranking.csv"
    fields = ["scheme", "rank", "method", "parameter", "fairnessGroupId", "spanBits", "bufferBits",
              "meanFer", "overallMeanFer", "worstPositionFer", "worstPosition", "bufferFraction", "deinterleaveTimeMeanNs",
              "decodeTimeMeanNs", "score", "paretoOptimal"]
    with ranking_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: item[key] for key in fields} for item in ranked)

    recommendations = {}
    for scheme in ("BCH", "CC"):
        candidates = [item for item in ranked if item["scheme"] == scheme and item["method"] != "NONE"]
        recommendations[scheme] = min(candidates, key=lambda item: item["rank"])
    method_recommendations = {}
    for item in ranked:
        key = (item["scheme"], item["method"])
        if key not in method_recommendations or item["rank"] < method_recommendations[key]["rank"]:
            method_recommendations[key] = item

    equal_span = defaultdict(list)
    for item in ranked:
        equal_span[(item["scheme"], item["fairnessGroupId"])].append(item)
    equal_span = {key: values for key, values in equal_span.items() if len({item["method"] for item in values}) >= 2}

    method_counts = {"BCH": 4, "CC": 3}
    comparison_groups = 31 * 3 * 6
    scheme_points = {scheme: comparison_groups * count for scheme, count in method_counts.items()}
    total_points = sum(scheme_points.values())
    average_cpu_ns = {scheme: sum(item["decodeTimeMeanNs"] + item["deinterleaveTimeMeanNs"] for item in metrics if item["scheme"] == scheme) /
                      len([item for item in metrics if item["scheme"] == scheme]) for scheme in ("BCH", "CC")}
    def runtime_hours(frames: int) -> float:
        return 1.5 * sum(scheme_points[s] * frames * average_cpu_ns[s] for s in ("BCH", "CC")) / 1e9 / 3600
    disk_max_mib = total_points * (2048 + 50 * 4096) / 1024 / 1024

    report = output_dir / "parameter_selection_report.md"
    with report.open("w", encoding="utf-8") as handle:
        handle.write("# S7 Stage09 参数选择与 Formal 资源估算\n\n")
        handle.write(f"原始预扫描：`{raw_path}`。候选排名：`{ranking_path}`。\n\n")
        handle.write(f"共 {len(fairness)} 个比较组，其中 {len(informative_keys)} 个组的候选 FER 存在差异并用于排名；所有饱和组仍保留在原始 CSV 和 overallMeanFer。评分越低越好；显式权重为区分组平均 FER 0.40、区分组六位置最坏 FER 0.30、缓冲比例 0.15、解交织 CPU 开销 0.15。另输出四目标 Pareto 标记。该排名是工程折中，不把不等跨度结果解释为纯方法差异。\n\n")
        for scheme in ("BCH", "CC"):
            item = recommendations[scheme]
            handle.write(f"- {scheme} 推荐候选：{item['method']}，参数 {item['parameter']}，排名 {item['rank']}，"
                         f"平均 FER={item['meanFer']:.6g}，最坏位置 FER={item['worstPositionFer']:.6g}（{item['worstPosition']}），"
                         f"bufferBits={item['bufferBits']}，平均解交织={item['deinterleaveTimeMeanNs']:.3f} ns。\n")
        handle.write("\n进入 Formal 的方法内冻结参数：\n\n")
        for (scheme, method), item in sorted(method_recommendations.items()):
            handle.write(f"- {scheme} / {method}: parameter={item['parameter']}（方法内综合排名最优；NONE 的 parameter=0）。\n")
        handle.write("\n## 等跨度方法公平对比\n\n")
        for (scheme, fairness_group), items in sorted(equal_span.items()):
            method_best = {}
            for item in items:
                if item["method"] not in method_best or item["score"] < method_best[item["method"]]["score"]:
                    method_best[item["method"]] = item
            summary = "；".join(f"{method}:参数 {item['parameter']}, FER={item['meanFer']:.6g}, buffer={item['bufferBits']}"
                               for method, item in sorted(method_best.items()))
            handle.write(f"- {scheme} / {fairness_group}：{summary}。\n")
        handle.write("\n## 方法内部参数敏感性\n\n完整排名 CSV 保留同一 method 的全部参数；选择报告不把不同 span 的差异解释为纯方法差异。BCH 分别扫描 CODEBLOCK depth 与 ROW_COLUMN rows；CC 分别扫描 SHORT_DEPTH depth 与 PSEUDORANDOM span。\n")
        handle.write("\n## Formal 矩阵\n\n")
        handle.write(f"- 每个编码的比较组数：31×3×6={comparison_groups}。\n")
        handle.write(f"- BCH 方案点数：{scheme_points['BCH']}；CC 方案点数：{scheme_points['CC']}；合计 {total_points}。\n")
        handle.write(f"- 两类编码比较组合计：{2*comparison_groups}。\n")
        handle.write(f"- 单线程估算：最少 1000 帧约 {runtime_hours(1000):.2f} 小时；按 5000 帧规划约 {runtime_hours(5000):.2f} 小时；50000 帧上限约 {runtime_hours(50000):.2f} 小时。\n")
        handle.write("- 估算使用预扫描 decode+deinterleave 均值并乘 1.5 调度/信道/I/O 系数；正式运行前应以 Release runner 小批量基准校准。\n")
        handle.write(f"- 最大磁盘估算约 {disk_max_mib:.1f} MiB，假设每方案点 2 KiB 汇总且每 1000 帧 checkpoint 4 KiB；不保存逐帧 trace。\n")
        handle.write("\n## Checkpoint 恢复\n\n每 1000 帧保存 configHash、caseKey、nextFrameIndex、累计计数、计时样本和 frameSequenceHash。恢复时先验证配置 hash 与 case key，再从 nextFrameIndex 继续；合并 checker 必须证明无重复、无跳帧且恢复前后 frameSequenceHash 一致。\n")
        handle.write("\n本报告只用于选择 Stage10 候选；Stage10 仍未授权。\n")

    validation = {
        "status": "PASS",
        "rowCount": len(rows),
        "candidateCount": len(metrics),
        "fairnessGroupCount": len(fairness),
        "informativeFairnessGroupCount": len(informative_keys),
        "equalSpanMethodComparisonGroups": [f"{scheme}:{group}" for scheme, group in sorted(equal_span)],
        "weights": WEIGHTS,
        "formal": {"comparisonGroupsPerScheme": comparison_groups, "comparisonGroupsTotal": 2 * comparison_groups,
                   "schemePoints": scheme_points, "totalSchemePoints": total_points,
                   "runtimeHoursMinFrames": runtime_hours(1000), "runtimeHoursPlannedFrames": runtime_hours(5000),
                   "runtimeHoursMaxFrames": runtime_hours(50000), "diskMaxMiB": disk_max_mib},
        "recommendations": {scheme: {key: value for key, value in item.items() if key in ("method", "parameter", "rank", "score")}
                            for scheme, item in recommendations.items()},
        "methodRecommendations": {f"{scheme}:{method}": {key: value for key, value in item.items() if key in ("parameter", "rank", "score")}
                                  for (scheme, method), item in method_recommendations.items()},
        "rawCsvAbsolutePath": str(raw_path),
        "rankingCsvAbsolutePath": str(ranking_path),
    }
    (output_dir / "prescan_validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS_S7_PRESCAN_ANALYSIS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
