#!/usr/bin/env python3
"""Read-only repository evidence scanner for the technical-report workspace.

The scanner never changes files outside ``报告``.  It inventories project
assets, records provenance signals, and writes conservative evidence ledgers.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

REPORT_NAME = "报告"
TEXT_EXTENSIONS = {".md", ".txt", ".csv", ".json", ".yaml", ".yml", ".toml", ".ini", ".hpp", ".h", ".cpp", ".c", ".py", ".m", ".cmake", ".log"}
SCAN_EXTENSIONS = TEXT_EXTENSIONS | {".pdf", ".docx", ".png", ".jpg", ".jpeg", ".bin", ".npy", ".npz", ".mat", ".dat", ".checkpoint"}
FORMAL_WORDS = ("formal", "final", "merged", "integration", "release")
ARCHIVE_WORDS = ("archive", "backup", "old", "temp", "patch_verify", "snapshot")
CSV_HEADERS = {
    "source": ["task", "stage", "category", "file_name", "absolute_path", "relative_path", "extension", "size_bytes", "modified_time", "created_time_if_available", "archive_flag", "generated_flag", "candidate_final_flag", "duplicate_group", "sha256_if_reasonable", "notes"],
    "result": ["task", "stage", "file_name", "relative_path", "result_kind", "formal_flag", "candidate_final_flag", "archive_flag", "rows", "columns", "key_columns", "notes"],
    "figure": ["figure_id", "task", "stage", "file_name", "relative_path", "format", "width_px", "height_px", "archive_flag", "candidate_final_flag", "possible_source_csv", "notes"],
    "formula": ["formula_id", "task", "stage", "topic", "expression_or_symbol", "source_file", "source_location", "source_priority", "verification_status", "notes"],
    "conclusion": ["conclusion_id", "task", "topic", "conclusion", "supporting_csv", "supporting_png", "supporting_report", "supporting_source_code", "parameter_scope", "snr_scope", "channel_scope", "platform_scope", "statistical_scope", "confidence", "limitation", "main_text_or_appendix", "verification_status", "notes"],
}


def git(root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=root, text=True, encoding="utf-8", errors="replace", stderr=subprocess.STDOUT).strip()
    except Exception as exc:
        return f"WARNING: {exc}"


def classify(path: Path, rel: str) -> tuple[str, str, str]:
    low = rel.lower().replace("\\", "/")
    archive = any(x in low for x in ARCHIVE_WORDS)
    generated = "/build/" in low or "/results/" in low
    if "附件3" in path.name or "信道编码" in path.name:
        category = "teacher_requirement"
    elif path.name in {"manifest.json", "validation_report.md", "known_issues.md", "stage_plan.md"}:
        category = "manifest"
    elif path.suffix.lower() in {".cpp", ".c", ".h", ".hpp"}:
        category = "source_code"
    elif "test" in low or "checker" in low:
        category = "test" if "checker" not in low else "checker"
    elif path.suffix.lower() in {".py", ".m"}:
        category = "script"
    elif path.suffix.lower() == ".csv":
        category = "formal_csv" if any(x in low for x in FORMAL_WORDS) else "summary_csv"
    elif path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
        category = "figure"
    elif path.suffix.lower() in {".bin", ".npy", ".npz", ".mat", ".dat", ".checkpoint"}:
        category = "checkpoint"
    else:
        category = "project_record"
    if "/comparison/s5/" in low: task = "S5"
    elif "/comparison/s6/" in low: task = "S6"
    elif "/comparison/s7/" in low: task = "S7"
    elif "/bch/" in low: task = "BCH"
    elif "/cc/" in low: task = "CC"
    elif "/ldpc/" in low: task = "LDPC"
    elif "/common/" in low: task = "COMMON"
    else: task = "UNKNOWN"
    stage_match = re.search(r"(?:^|[/_\\])(s[1-7]|stage\d+|bch\d+)(?:[/_\\]|$)", low)
    return task, (stage_match.group(1).upper() if stage_match else "UNKNOWN"), category


def sha256(path: Path) -> str:
    # Full hashes are useful for small evidence and source files.  Do not turn
    # a catalogue operation into a multi-minute read of simulation artifacts.
    if path.stat().st_size > 1024 * 1024:
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def text_excerpt(path: Path) -> str:
    try:
        if path.suffix.lower() == ".docx":
            with zipfile.ZipFile(path) as zf:
                raw = zf.read("word/document.xml")
            root = ET.fromstring(raw)
            return " ".join(t.text or "" for t in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"))
        if path.suffix.lower() in TEXT_EXTENSIONS and path.stat().st_size <= 4 * 1024 * 1024:
            return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    return ""


def image_size(path: Path) -> tuple[str, str]:
    try:
        with path.open("rb") as f:
            head = f.read(32)
        if head.startswith(b"\x89PNG\r\n\x1a\n"):
            return str(int.from_bytes(head[16:20], "big")), str(int.from_bytes(head[20:24], "big"))
        if head[:2] == b"\xff\xd8":
            # Conservative JPEG marker parser.
            with path.open("rb") as f:
                f.read(2)
                while True:
                    marker = f.read(2)
                    if len(marker) != 2: break
                    if marker[0] != 0xff: continue
                    length = int.from_bytes(f.read(2), "big")
                    if marker[1] in range(0xc0, 0xc4):
                        data = f.read(5)
                        return str(int.from_bytes(data[3:5], "big")), str(int.from_bytes(data[1:3], "big"))
                    f.seek(max(0, length - 2), 1)
    except Exception:
        pass
    return "", ""


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    report = root / REPORT_NAME
    evidence = report / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    log: list[str] = [f"scan started: {datetime.now().isoformat()}"]
    source_rows: list[dict] = []; result_rows: list[dict] = []; figure_rows: list[dict] = []; formula_rows: list[dict] = []
    files: list[tuple[Path, str]] = []
    skipped_dirs = {".git", "__pycache__", ".vscode", ".idea", REPORT_NAME}
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skipped_dirs]
        base = Path(directory)
        for name in filenames:
            path = base / name
            suffix = path.suffix.lower()
            if suffix not in SCAN_EXTENSIONS and name != "CMakeLists.txt":
                continue
            files.append((path, path.relative_to(root).as_posix()))
    hashes: dict[str, list[str]] = {}
    for path, rel in files:
        try:
            stat = path.stat(); suffix = path.suffix.lower(); task, stage, category = classify(path, rel)
            archive = any(x in rel.lower() for x in ARCHIVE_WORDS)
            candidate = (not archive and (category in {"formal_csv", "figure", "manifest"} or any(x in rel.lower() for x in FORMAL_WORDS)))
            digest = sha256(path) if stat.st_size <= 1024 * 1024 and category in {"source_code", "script", "manifest", "project_record"} else ""
            if digest: hashes.setdefault(digest, []).append(rel)
            source_rows.append({"task": task, "stage": stage, "category": category, "file_name": path.name, "absolute_path": str(path.resolve()), "relative_path": rel, "extension": suffix or path.name, "size_bytes": stat.st_size, "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(), "created_time_if_available": datetime.fromtimestamp(stat.st_ctime).isoformat(), "archive_flag": str(archive).upper(), "generated_flag": str("/build/" in rel.lower() or "/results/" in rel.lower()).upper(), "candidate_final_flag": str(candidate).upper(), "duplicate_group": "", "sha256_if_reasonable": digest, "notes": ""})
            if suffix == ".csv":
                try:
                    with path.open(encoding="utf-8-sig", errors="replace", newline="") as f:
                        reader = csv.reader(f); columns = next(reader, []); row_count = sum(1 for _ in reader)
                    result_rows.append({"task": task, "stage": stage, "file_name": path.name, "relative_path": rel, "result_kind": category, "formal_flag": str("formal" in rel.lower()).upper(), "candidate_final_flag": str(candidate).upper(), "archive_flag": str(archive).upper(), "rows": row_count, "columns": len(columns), "key_columns": "|".join(columns[:12]), "notes": ""})
                except Exception as exc: log.append(f"WARNING csv {rel}: {exc}")
            if suffix in {".png", ".jpg", ".jpeg"}:
                width, height = image_size(path)
                figure_rows.append({"figure_id": f"FIG-{len(figure_rows)+1:04d}", "task": task, "stage": stage, "file_name": path.name, "relative_path": rel, "format": suffix[1:].upper(), "width_px": width, "height_px": height, "archive_flag": str(archive).upper(), "candidate_final_flag": str(candidate).upper(), "possible_source_csv": "", "notes": ""})
            excerpt = text_excerpt(path)
            if excerpt and category in {"source_code", "script", "project_record"}:
                for num, line in enumerate(excerpt.splitlines(), 1):
                    if re.search(r"(?:E[bss]/N0|Es/N0|AWGN|LLR|sigma|BPSK|BER|FER)", line, re.I) and ("=" in line or "formula" in line.lower() or "llr" in line.lower()):
                        formula_rows.append({"formula_id": f"FOR-{len(formula_rows)+1:04d}", "task": task, "stage": stage, "topic": "implementation expression", "expression_or_symbol": line.strip()[:300], "source_file": rel, "source_location": f"line {num}", "source_priority": "source_code" if category == "source_code" else "script_or_record", "verification_status": "UNREVIEWED", "notes": "Automated candidate; verify signs, units and rate convention before report use."})
                        if len(formula_rows) >= 2000: break
        except Exception as exc:
            log.append(f"WARNING file {rel}: {exc}")
    for row in source_rows:
        if row["sha256_if_reasonable"] and len(hashes[row["sha256_if_reasonable"]]) > 1:
            row["duplicate_group"] = "DUP-" + row["sha256_if_reasonable"][:12]
    write_csv(evidence / "source_inventory.csv", CSV_HEADERS["source"], source_rows)
    write_csv(evidence / "result_inventory.csv", CSV_HEADERS["result"], result_rows)
    write_csv(evidence / "figure_inventory.csv", CSV_HEADERS["figure"], figure_rows)
    write_csv(evidence / "formula_inventory.csv", CSV_HEADERS["formula"], formula_rows)
    conclusions = []
    for row in result_rows:
        if row["candidate_final_flag"] == "TRUE":
            conclusions.append({"conclusion_id": f"CE-{len(conclusions)+1:04d}", "task": row["task"], "topic": "candidate result", "conclusion": "No conclusion asserted: formal-result candidate requires numerical review.", "supporting_csv": row["relative_path"], "supporting_png": "", "supporting_report": "", "supporting_source_code": "", "parameter_scope": "UNKNOWN", "snr_scope": "UNKNOWN", "channel_scope": "UNKNOWN", "platform_scope": "UNKNOWN", "statistical_scope": "See source CSV", "confidence": "UNREVIEWED", "limitation": "Automated inventory only.", "main_text_or_appendix": "TBD", "verification_status": "PENDING_REVIEW", "notes": ""})
    write_csv(evidence / "conclusion_evidence_matrix.csv", CSV_HEADERS["conclusion"], conclusions)
    teacher = [r for r in source_rows if r["category"] == "teacher_requirement" and r["archive_flag"] == "FALSE"]
    teacher_lines = ["# 教师原始要求台账", "", "本台账只登记已定位到的原始文件；PDF 内容待使用可审计的文本提取或人工页码复核后填充。", "", "| 要求编号 | 原始要求 | 来源文件 | 页码/位置 | 对应任务 | 当前实现状态 | 备注 |", "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(teacher, 1): teacher_lines.append(f"| TR-{i:03d} | 待逐页提取 | `{r['relative_path']}` | 待核验 | S1--S7 | UNKNOWN | 已定位原始要求文件 |")
    if not teacher: teacher_lines.append("| TR-001 | 未定位到非归档的教师原始要求文件 | — | — | — | UNKNOWN | 需要补充 |")
    (evidence / "teacher_requirements.md").write_text("\n".join(teacher_lines)+"\n", encoding="utf-8")
    state = ["# 仓库状态", "", f"- 根目录：`{root}`", f"- 分支：`{git(root, 'branch', '--show-current')}`", f"- HEAD：`{git(root, 'rev-parse', 'HEAD')}`", "- git status：", "```text", git(root, 'status', '--short') or "(clean)", "```", "- worktree：", "```text", git(root, 'worktree', 'list'), "```"]
    (evidence / "repository_state.md").write_text("\n".join(state)+"\n", encoding="utf-8")
    candidate_results = [r for r in result_rows if r["candidate_final_flag"] == "TRUE"]
    selection = ["# 最终结果候选识别", "", "以下为自动识别的候选，必须逐项以正式 CSV、关联源码和审计记录复核后才能作为报告结论。归档、备份和临时目录已排除。", "", "| 编号 | 任务 | 候选 CSV | 依据 | 状态 |", "|---|---|---|---|---|"]
    selection += [f"| FR-{i:03d} | {r['task']} | `{r['relative_path']}` | 路径含 formal/final/merged/integration，且非 archive | 待人工复核 |" for i, r in enumerate(candidate_results, 1)]
    (evidence / "final_result_selection.md").write_text("\n".join(selection)+"\n", encoding="utf-8")
    inc = "# 不一致登记\n\n本文件只登记扫描规则已触发的待核验项，不修改原始结果。\n\n## INC-001 归档与正式候选隔离\n\n涉及文件：所有路径含 `archive`、`backup`、`old`、`temp`、`patch_verify` 或 `snapshot` 的结果。\n\n问题描述：这些材料可能与现行结果同名或重复。\n\n实际证据：`source_inventory.csv` 中 `archive_flag=TRUE`。\n\n影响：不得作为正式报告的唯一结论依据。\n\n报告中建议处理方式：仅作历史导航，正式结论回查非归档 CSV 与源码。\n\n是否需要补实验：否；先完成版本与证据复核。\n\n状态：OPEN。\n"
    (evidence / "inconsistency_register.md").write_text(inc, encoding="utf-8")
    missing = "# 缺失资料清单\n\n## IMPORTANT — 教师要求逐页页码索引\n\n已定位到原始要求文件，但本自动扫描未执行 PDF OCR；正式写作前需逐页提取并复核要求。\n\n## IMPORTANT — 最终候选数值复核\n\n候选 CSV 已建立索引，但尚未逐项核对参数、图源和审计 Gate。\n\n## OPTIONAL — Visio 流程图\n\n本轮仅建立占位机制，未生成正式 Visio 图片。\n"
    (evidence / "missing_materials.md").write_text(missing, encoding="utf-8")
    visio = "# Visio 图片规划\n\n| figure_id | file_name | report_section | title | purpose | required_elements | source_code_reference | source_parameter_reference | recommended_aspect_ratio | status |\n|---|---|---|---|---|---|---|---|---|---|\n"
    plans = [("VIS-001","figures/visio/common/overall_scenario_architecture.png","02","总体场景架构"),("VIS-002","figures/visio/common/unified_simulation_chain.png","03","统一仿真链路"),("VIS-003","figures/visio/bch/bch_segmented_vs_block.png","04","BCH 分块与整块"),("VIS-004","figures/visio/bch/bch_decoder_comparison.png","08","BCH 译码器比较"),("VIS-005","figures/visio/cc/cc_encoding_decoding_chain.png","05","卷积编码译码链路"),("VIS-006","figures/visio/cc/block_vs_slot_continuous.png","05","整块与时隙连续"),("VIS-007","figures/visio/cc/sliding_window_wsd.png","05","滑窗 W/S/D"),("VIS-008","figures/visio/ldpc/direct_bg2_ldpc_chain.png","06","Direct BG2 LDPC 链路"),("VIS-009","figures/visio/ldpc/bp_vs_nms_decoder.png","08","BP 与 NMS"),("VIS-010","figures/visio/multichannel/six_channel_models.png","07","六类信道模型"),("VIS-011","figures/visio/interleaving/interleaving_position.png","09","交织位置"),("VIS-012","figures/visio/interleaving/bch_interleavers.png","09","BCH 交织器"),("VIS-013","figures/visio/interleaving/cc_trellis_step_interleaver.png","09","CC 栅格步进交织"),("VIS-014","figures/visio/common/final_scheme_selection.png","10","方案选择")]
    for p in plans: visio += f"| {p[0]} | `{p[1]}` | {p[2]} | {p[3]} | 待补 | 待依据扫描补充 | TBD | TBD | 16:9 | PLANNED |\n"
    (evidence / "visio_figure_plan.md").write_text(visio, encoding="utf-8")
    report_text = f"# 本地资料扫描报告\n\n## 1. 扫描范围\n扫描了仓库内受支持文件扩展名；不读取大型二进制内容，不运行仿真。\n\n## 2. 仓库状态\n见 `repository_state.md`。\n\n## 3--10. 教师要求、Common、BCH、卷积码、LDPC、S5、S6、S7\n见四类库存及最终候选台账；结论均待人工数值复核。\n\n## 11. 最终结果识别情况\n候选 {len(candidate_results)} 项，见 `final_result_selection.md`。\n\n## 12--14. CSV、PNG、公式\nCSV {len(result_rows)} 个，PNG/JPEG {len(figure_rows)} 个，公式候选 {len(formula_rows)} 项。\n\n## 15--18. 结论证据、差异、缺失、Visio\n见同名 evidence 文件。\n\n## 19. LaTeX 骨架状态\n已创建，需另行编译检查。\n\n## 20. 后续建议\n先完成教师要求逐页复核与正式结果候选数值复查，再开始正文。\n"
    (evidence / "scan_report.md").write_text(report_text, encoding="utf-8")
    status = "NOT_RUN"; latexmk = shutil.which("latexmk")
    manifest = {"repository_root": str(root), "report_root": str(report), "scan_time": datetime.now(timezone.utc).isoformat(), "git_branch": git(root, "branch", "--show-current"), "git_commit": git(root, "rev-parse", "HEAD"), "file_count": len(source_rows), "csv_count": len(result_rows), "png_count": len(figure_rows), "markdown_count": sum(r["extension"] == ".md" for r in source_rows), "source_code_count": sum(r["category"] == "source_code" for r in source_rows), "formal_result_count": sum(r["formal_flag"] == "TRUE" for r in result_rows), "candidate_final_result_count": len(candidate_results), "archive_file_count": sum(r["archive_flag"] == "TRUE" for r in source_rows), "warning_count": len([x for x in log if "WARNING" in x]), "error_count": 0, "latex_compile_status": status if not latexmk else "AVAILABLE_NOT_RUN", "modified_original_file_count": 0, "generated_files": [p.name for p in evidence.iterdir()]}
    (evidence / "scan_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    (evidence / "scan_execution.log").write_text("\n".join(log)+"\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
