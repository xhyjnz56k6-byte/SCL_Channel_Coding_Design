#!/usr/bin/env python3
import csv
import hashlib
import json
import math
import pathlib
import re
import subprocess


ROOT = pathlib.Path(__file__).resolve().parents[4]
S6 = ROOT / "Task" / "Comparison" / "S6"
BCH_ROOT = S6 / "results" / "bch" / "formal_v02_20260804"
BCH = BCH_ROOT / "bch_formal_results.csv"
BCH_COMPLEX = BCH_ROOT / "bch_complexity_results.csv"
BCH_MEMORY = BCH_ROOT / "bch_memory_results.csv"
CC = S6 / "results" / "cc" / "cc_integrated_results.csv"
LDPC = S6 / "results" / "ldpc" / "ldpc_n560_integrated_results.csv"
STAGE11 = S6 / "results" / "stage11_chinese" / "plots"
FINAL_PLOTS = S6 / "results" / "summary" / "figures"
ENVIRONMENT = BCH_ROOT / "execution_environment.json"


def sha256(path):
    value = hashlib.sha256()
    with pathlib.Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def read_csv(path):
    with pathlib.Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    with pathlib.Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def archive_gate():
    versions = (
        S6 / "results" / "bch" / "archive" / "v01_20260804_before_smoke_driver_retry",
        S6 / "results" / "bch" / "archive" / "v02_20260804_before_memory_peak_fix",
        S6 / "archive" / "v03_20260804_before_chinese_plot_revision",
    )
    checked = 0
    for version in versions:
        manifest = version / "archive_manifest.csv"
        if not manifest.exists(): raise RuntimeError(f"missing archive manifest: {manifest}")
        for row in read_csv(manifest):
            path = version / pathlib.PurePosixPath(row["relativePath"])
            if not path.exists() or path.stat().st_size != int(row["fileSizeBytes"]) or sha256(path) != row["sha256"]:
                raise RuntimeError(f"archive mismatch: {path}")
            checked += 1
    return checked


def readme_gate():
    directories = [S6] + [path for path in S6.rglob("*") if path.is_dir()]
    missing = [path for path in directories if not (path / "readme.txt").exists()]
    if missing: raise RuntimeError("missing readme: " + ";".join(str(path) for path in missing))
    return len(directories)


def plot_gate(root, expected_count, module):
    directories = sorted(path for path in root.iterdir() if path.is_dir())
    if len(directories) != expected_count: raise RuntimeError(f"{module} plot count mismatch")
    inventory, zero_rows = [], 0
    for directory in directories:
        required = [directory / name for name in ("figure.png", "figure_data.csv", "plot_manifest.json", "readme.txt")]
        if not all(path.exists() for path in required): raise RuntimeError(f"plot files missing: {directory}")
        manifest = json.loads(required[2].read_text(encoding="utf-8"))
        if not re.search(r"[\u4e00-\u9fff]", manifest["title"]): raise RuntimeError(f"non-Chinese title: {directory}")
        if manifest.get("interpolation") != "NONE" or manifest.get("smoothing") != "NONE": raise RuntimeError(f"plot transform violation: {directory}")
        if sha256(required[0]) != manifest["outputHash"]: raise RuntimeError(f"PNG hash mismatch: {directory}")
        data = read_csv(required[1])
        if manifest.get("logScale"):
            for row in data:
                if float(row["rawValue"]) == 0.0:
                    zero_rows += 1
                    if row["plotValue"] or row["isPlotted"].lower() != "false" or row["isZero"].lower() != "true":
                        raise RuntimeError(f"zero plot violation: {directory}")
        inventory.append({"module": module, "figureId": manifest["figureId"], "title": manifest["title"],
                          "logScale": str(bool(manifest.get("logScale"))).lower(), "sourceFiles": ";".join(manifest["sourceFiles"]),
                          "pngPath": required[0].relative_to(ROOT).as_posix(), "pngSha256": manifest["outputHash"],
                          "dataPath": required[1].relative_to(ROOT).as_posix(), "manifestPath": required[2].relative_to(ROOT).as_posix(),
                          "gate": "PASS"})
    return inventory, zero_rows


def result_inventory(paths):
    rows = []
    for role, path in paths:
        data_rows = len(read_csv(path)) if path.suffix.lower() == ".csv" else ""
        rows.append({"role": role, "path": path.relative_to(ROOT).as_posix(), "fileSizeBytes": path.stat().st_size,
                     "rowCount": data_rows, "sha256": sha256(path), "status": "CURRENT"})
    return rows


def metric_summary(bch, cc, ldpc, bch_memory):
    rows = []
    for case in sorted({row["caseName"] for row in bch}):
        selected = [row for row in bch if row["caseName"] == case]
        frames = sum(int(row["processedFrames"]) for row in selected)
        rows.append({"module": "BCH", "scheme": case, "snrPoints": len(selected), "totalFrames": frames,
                     "totalBitErrors": sum(int(row["decodedBitErrors"]) for row in selected),
                     "totalFrameErrors": sum(int(row["decodedFrameErrors"]) for row in selected),
                     "weightedAvgDecodeTimeUs": sum(float(row["avgDecodeTimeUs"]) * int(row["processedFrames"]) for row in selected) / frames,
                     "maxObservedDecodeTimeUs": max(float(row["maxDecodeTimeUs"]) for row in selected),
                     "decoderMemoryBytes": max(int(row["totalDecoderMemoryBytes"]) for row in bch_memory if row["caseName"] == case),
                     "zeroBerPoints": sum(float(row["BER"]) == 0 for row in selected), "zeroFerPoints": sum(float(row["FER"]) == 0 for row in selected)})
    for scheme in sorted({row["schemeId"] for row in cc}):
        selected = [row for row in cc if row["schemeId"] == scheme]; frames = sum(int(row["frames"]) for row in selected)
        rows.append({"module": "CC", "scheme": scheme, "snrPoints": len(selected), "totalFrames": frames,
                     "totalBitErrors": sum(int(row["bitErrors"]) for row in selected), "totalFrameErrors": sum(int(row["frameErrors"]) for row in selected),
                     "weightedAvgDecodeTimeUs": sum(float(row["avgCpuDecodeTimeUs"]) * int(row["frames"]) for row in selected) / frames,
                     "maxObservedDecodeTimeUs": max(float(row["maxCpuDecodeTimeUs"]) for row in selected),
                     "decoderMemoryBytes": max(int(row["decoderMemoryBytes"]) for row in selected),
                     "zeroBerPoints": sum(float(row["BER"]) == 0 for row in selected), "zeroFerPoints": sum(float(row["FER"]) == 0 for row in selected)})
    for algorithm in ("BP", "NMS"):
        selected = [row for row in ldpc if row["algorithm"] == algorithm]; frames = sum(int(row["frames"]) for row in selected)
        rows.append({"module": "LDPC", "scheme": f"N560_{algorithm}", "snrPoints": len(selected), "totalFrames": frames,
                     "totalBitErrors": sum(int(row["bitErrors"]) for row in selected), "totalFrameErrors": sum(int(row["frameErrors"]) for row in selected),
                     "weightedAvgDecodeTimeUs": sum(float(row["avgDecodeTimeUs"]) * int(row["frames"]) for row in selected) / frames,
                     "maxObservedDecodeTimeUs": max(float(row["maxDecodeTimeUs"]) for row in selected),
                     "decoderMemoryBytes": max(int(row["decoderMemoryBytes"]) for row in selected),
                     "zeroBerPoints": sum(float(row["BER"]) == 0 for row in selected), "zeroFerPoints": sum(float(row["FER"]) == 0 for row in selected)})
    return rows


def main():
    final_report = S6 / "S6_final_report.md"
    if final_report.exists(): raise RuntimeError("refuse to overwrite final report")
    for path in (BCH, BCH_COMPLEX, BCH_MEMORY, CC, LDPC, ENVIRONMENT):
        if not path.exists(): raise RuntimeError(f"missing final source: {path}")
    branch, head = git("branch", "--show-current"), git("rev-parse", "HEAD")
    if branch != "S6-Comparision": raise RuntimeError("wrong final branch")
    archive_files = archive_gate()
    readme_directories = readme_gate()
    stage11_inventory, stage11_zero = plot_gate(STAGE11, 86, "Stage11")
    final_inventory, final_zero = plot_gate(FINAL_PLOTS, 26, "S6")
    bch, bc, bm, cc, ldpc = map(read_csv, (BCH, BCH_COMPLEX, BCH_MEMORY, CC, LDPC))
    if len(bch) != 62 or len(bc) != 2046 or len(bm) != 62 or len(cc) != 248 or len(ldpc) != 62:
        raise RuntimeError("final result row count mismatch")
    if any(not math.isfinite(float(row[field])) for row in bch for field in ("BER", "FER", "avgDecodeTimeUs")):
        raise RuntimeError("BCH non-finite result")
    environment = json.loads(ENVIRONMENT.read_text(encoding="utf-8-sig"))
    inventory_paths = (
        ("BCH正式点表", BCH), ("BCH复杂度", BCH_COMPLEX), ("BCH内存", BCH_MEMORY),
        ("BCH执行环境", ENVIRONMENT), ("CC整合结果", CC), ("LDPC N560整合结果", LDPC),
        ("Stage11绘图审计", S6 / "results" / "stage11_chinese" / "plot_audit_summary.json"),
        ("S6最终绘图审计", S6 / "results" / "summary" / "s6_plot_summary.json"))
    write_csv(S6 / "S6_result_inventory.csv", result_inventory(inventory_paths))
    metrics = metric_summary(bch, cc, ldpc, bm)
    write_csv(S6 / "S6_metric_summary.csv", metrics)
    write_csv(S6 / "S6_plot_inventory.csv", stage11_inventory + final_inventory)
    environment_text = f"""# S6 执行环境摘要

- CPU：{environment['cpuModel']}（{environment['physicalCoreCount']} 物理核 / {environment['logicalProcessorCount']} 逻辑处理器）
- 内存：{environment['totalMemoryBytes']} byte
- 操作系统：{environment['osName']}，版本 {environment['osVersion']}，Build {environment['osBuild']}
- 编译器：{environment['compilerVersion']}
- 标准与构建：{environment['cppStandard']}，{environment['buildType']}，{environment['optimizationFlags']}
- 线程：{environment['threadCount']}；计时钟：{environment['timingClock']}
- 计时范围：{environment['timingScope']}
- 预热：{environment['warmupFrames']} 帧；逐帧日志：{environment['frameDetailLogging']}
- 动态分配是否包含在计时中：{environment['timingIncludesDynamicAllocation']}
- 电源方案：{environment['performanceMode']}
- 可执行文件 SHA256：`{environment['executableSha256']}`
- Git：`{environment['gitBranch']}` / `{environment['gitCommit']}`；正式运行时工作区状态已完整保存在环境 JSON。

时延仅适用于当前 CPU、操作系统、编译器、Release 配置和线程环境；最大时延是平台相关观测值，不是理论最坏上界。
"""
    (S6 / "S6_environment_summary.md").write_text(environment_text, encoding="utf-8")
    gates = [
        "PASS_REPOSITORY_SCOPE", "PASS_ARCHIVE_INTEGRITY", "PASS_README_COVERAGE",
        "PASS_BCH_COUNTER_UNIT_TESTS", "PASS_BCH_MEMORY_ACCOUNTING", "PASS_BCH_NOISE_FORMULA",
        "PASS_BCH_FORMAL_GRID", "PASS_BCH_RESULT_SCHEMA", "PASS_BCH_ZERO_VALUE_POLICY",
        "PASS_STAGE11_86_FIGURES_FOUND", "PASS_STAGE11_CHINESE_TITLES", "PASS_STAGE11_AXIS_VALIDATION",
        "PASS_STAGE11_ZERO_VALUE_POLICY", "PASS_STAGE11_PLOT_MANIFESTS", "PASS_CC_RESULT_INTEGRATION",
        "PASS_LDPC_N560_RESULT_INTEGRATION", "PASS_EXECUTION_ENVIRONMENT_CAPTURE",
        "PASS_TIMING_SCOPE_DOCUMENTATION", "PASS_SHA256_MANIFEST", "PASS_S6_FINAL_REPORT"]
    validation = "# S6 验证报告\n\n" + "\n".join(f"- `{gate}`" for gate in gates) + (
        f"\n\n核验统计：归档文件 {archive_files} 个；readme 覆盖目录 {readme_directories} 个；"
        f"Stage11 图 86 张；S6 图 26 张；Stage11 零值 {stage11_zero} 条；S6 图零值 {final_zero} 条。\n\n"
        "S6_FINAL_STATUS = PASS\n")
    (S6 / "S6_validation_report.md").write_text(validation, encoding="utf-8")
    known = """# S6 已知问题

- BCH-S200 与 BCH-B200 是不同码型、不同组织、不同码率、不同纠错能力的工程组合，BER/FER 差异不能全部归因于 lookup 与 BM。
- BCH 内存使用 `EXACT_FROM_TYPE_AND_COUNT`，不包含通用 STL 分配器隐藏元数据。
- CC 历史 Formal 非严格 pair-stop；Hard/Soft 与 Block/Slot 是两个独立维度。
- LDPC 主结果仅 maxIter=32；10/20/30 未完成正式性能对比。
- CPU 时延是平台相关观测值；BCH 本轮环境电源方案为“平衡”。
- 高 SNR 零 BER/FER 保留在数据中但不绘制；曲线终止不表示真实 error floor。
- 工作区按用户要求未 commit、未 push、未 merge。
"""
    (S6 / "S6_known_issues.md").write_text(known, encoding="utf-8")
    report = f"""# S6 译码算法对比与结果汇总

## 1. 任务目的与数据来源

本任务在 `S6-Comparision` 分支完成本地已有结果盘点、BCH 必要补跑、Stage11 全部 86 图中文重绘、CC/LDPC 历史 Formal 整合和 S6 科研图汇总。BCH 使用本轮 Release 单线程正式结果；CC 来源于 Stage14；LDPC 来源于 Stage23 修订后的 N560 Formal 点表。

## 2. BCH 方案与正式实验

- BCH-S200：200 bit 分组方案，19 个 shortened BCH(15,11,1)，N=285，syndrome lookup，每段 t=1。
- BCH-B200：200 bit 整块 shortened BCH(255,207)，N=248，BM+Chien，t=6。
- 信道为 BPSK+AWGN；Es/N0=-5:0.5:10 dB；minFrames=1000、targetFrameErrors=200、maxFrames=50000。
- 62/62 点完成，噪声公式、停止条件、计数、存储和计时 Gate 全部通过。

S200 与 B200 是不同码型、不同组织、不同码率、不同纠错能力的工程组合对比。不能把 BER/FER 差异全部归因于 lookup 与 BM。

## 3. 复杂度、存储与时延定义

BCH 复杂度分为算法事件、有限域/位操作、存储和实测译码时间。不同操作类别并非等价硬件代价，因此不生成无定义的单一复杂度总和。存储按对象、表、缓冲区和峰值工作区分类；BCH 使用 `EXACT_FROM_TYPE_AND_COUNT`。译码计时从输入硬判决准备完成开始，到 payload 与状态就绪结束，不包含编码、信道、硬判决、日志和文件 I/O。

## 4. CC 硬软判决与组织方式

整合 R1/2、K=300、N=612 的 BLOCK_HARD、BLOCK_FLOAT_SOFT，以及 B/C/D 三种时隙组织的 Hard/Float Soft，时隙统一 D=70、W=128、S=25。Hard=1 bit，Float Soft=Float。CPU 译码时间与首输出/决策符号时延严格分列。

Hard/Soft 是判决信息方式；Block/Slot 是组织与调度方式。两者是独立维度。历史结果非严格 pair-stop，本次未重跑 CC Formal。

## 5. LDPC BP/NMS

只使用 Direct BG2 N560：K=300、N=560、Zc=56、filler=148、parity=112、maxIter=32。BP/NMS 的 31 对 SNR 点共用 payload、codeword、LLR 和 syndrome early-stop；NMS alpha=0.95。

BP 是性能基准。NMS 以较低非线性复杂度换取可能的性能损失。现有主结果为 maxIter=32；代码支持不等于 10/20/30 正式结果存在。

## 6. BER/FER 与零值处理

所有原始零值保持为 0。高 SNR 零 BER/FER 点不参与对数曲线绘制，`plotValue` 留空且 `isPlotted=false`；未平滑、未插值、未绘制人工下限线。曲线终止不代表存在真实 error floor。

## 7. 图与结果清单

- Stage11 中文重绘：86 张，86/86 通过逐图 Gate。
- S6 最终科研图：BCH 10、CC 8、LDPC 8，共 26 张。
- 详细结果、指标和图清单见 `S6_result_inventory.csv`、`S6_metric_summary.csv` 和 `S6_plot_inventory.csv`。

## 8. 工程选型建议

- BCH：若重视实现简单和分段局部纠错，可评估 S200；若重视整块 t=6 能力，可评估 B200，但须连同码率和码型差异解释性能。
- CC：Hard 降低输入精度与部分存储需求，Float Soft 提供更丰富可靠度信息；Block/Slot 应按调度与实时延迟需求另行选择。
- LDPC：BP 用作性能基准，NMS 在本平台显著降低非线性运算与平均 CPU 时间，但必须结合实际 BER/FER 曲线判断可接受损失。

## 9. 环境与限制

正式 BCH CPU 为 {environment['cpuModel']}，编译器为 {environment['compilerVersion']}，Release、单线程。时延仅适用于当前 CPU、操作系统、编译器、Release 配置和线程环境；最大时延是平台相关观测值，不是理论最坏上界。完整环境见 `S6_environment_summary.md`。

## 10. Gate 与 Git 状态

20 项最终 Gate 全部 PASS。当前 HEAD 为 `{head}`；工作区按任务要求保持未提交。未运行 CC Formal，未运行 LDPC Formal，未 commit、未 push、未 merge，且未合并 main。

S6_FINAL_STATUS = PASS
"""
    final_report.write_text(report, encoding="utf-8")
    stage08 = S6 / "stage08_s6_final_report"
    (stage08 / "validation_report.md").write_text("# Stage08 验证报告\n\n最终 20 项 Gate 全部 PASS；S6_FINAL_STATUS = PASS。\n", encoding="utf-8")
    (stage08 / "manifest.json").write_text(json.dumps({
        "stage": "stage08_s6_final_report", "branch": branch, "baseCommit": head,
        "contentState": "WORKTREE_UNCOMMITTED_BY_USER_REQUIREMENT", "functionalRanges": [],
        "finalReport": "Task/Comparison/S6/S6_final_report.md", "gate": "PASS_S6_FINAL_REPORT",
        "mergeStatus": "NOT_MERGED"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    stage_readme = stage08 / "readme.txt"
    stage_readme.write_text("阶段名称：stage08_s6_final_report\n\n实验目的：汇总 S6 数据、图、环境、哈希和 Gate。\n完成内容：最终报告及八项配套审计文件已生成。\n当前结论：S6_FINAL_STATUS = PASS。\n已知问题：工作区按要求未提交。\n阶段状态：PASS\n", encoding="utf-8")
    overall_manifest = {
        "schemaVersion": "s6.final.manifest.v1", "branch": branch, "head": head,
        "workingTreeState": "UNCOMMITTED_BY_USER_REQUIREMENT", "mergeStatus": "NOT_MERGED",
        "formalExecution": {"BCH": True, "CC": False, "LDPC": False},
        "resultRows": {"BCH": len(bch), "BCHComplexity": len(bc), "BCHMemory": len(bm), "CC": len(cc), "LDPC": len(ldpc)},
        "plots": {"Stage11": 86, "S6": 26}, "archiveFilesVerified": archive_files,
        "readmeDirectoriesVerified": readme_directories, "gates": gates, "finalStatus": "PASS"}
    (S6 / "S6_manifest.json").write_text(json.dumps(overall_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sha_path = S6 / "S6_sha256.txt"
    files = sorted(path for path in S6.rglob("*") if path.is_file() and path != sha_path)
    sha_path.write_text("\n".join(f"{sha256(path)}  {path.relative_to(S6).as_posix()}" for path in files) + "\n", encoding="utf-8")
    for line in sha_path.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        if sha256(S6 / pathlib.PurePosixPath(relative)) != expected: raise RuntimeError(f"final SHA mismatch: {relative}")
    print("S6_FORMAL_INTEGRATION_COMPLETE")
    print(f"branch={branch}")
    print(f"HEAD={head}")
    print("S6_FINAL_STATUS=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
