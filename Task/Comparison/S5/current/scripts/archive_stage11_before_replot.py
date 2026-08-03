import hashlib
import json
import pathlib
import shutil

S5 = pathlib.Path(__file__).resolve().parents[2]
SOURCE = S5 / "results" / "stage11"
ARCHIVE_ROOT = SOURCE / "archive"
STAGE11 = S5 / "stages" / "stage11_plot_audit_and_final_integration"
SCRIPT = S5 / "current" / "scripts" / "stage11_analysis.py"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    numbers = []
    for item in ARCHIVE_ROOT.glob("v??_*"):
        try:
            numbers.append(int(item.name[1:3]))
        except ValueError:
            pass
    version = max(numbers, default=0) + 1
    target = ARCHIVE_ROOT / f"v{version:02d}_20260803_before_chinese_replot_and_aggregate"
    if target.exists():
        raise RuntimeError(f"archive already exists: {target}")
    target.mkdir()
    shutil.copytree(SOURCE / "plots", target / "plots")
    copied = []
    for name in ("plot_audit_summary.json", "s5_channel_loss_table.csv", "s5_latency_comparison.csv",
                 "s5_robustness_summary.csv", "s5_scenario_recommendation.csv"):
        shutil.copy2(SOURCE / name, target / name); copied.append(name)
    for name in ("validation_report.md", "manifest.json"):
        shutil.copy2(STAGE11 / name, target / f"stage11_{name}"); copied.append(f"stage11_{name}")
    shutil.copy2(SCRIPT, target / "stage11_analysis.py"); copied.append("stage11_analysis.py")
    files = sorted(path for path in target.rglob("*") if path.is_file())
    manifest = {
        "schemaVersion": "s5.stage11.archive.v1", "reason": "archive English plots before Chinese replot and Aggregate",
        "sourceFormalCsvSha256": "dbeb75842f8ecd5874e58153f908505884395750614ab75a6a33cdc3e3739947",
        "sourcePlotScriptSha256": sha256(SCRIPT), "fileCountBeforeManifests": len(files),
        "topLevelEvidence": copied,
    }
    (target / "archive_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files = sorted(path for path in target.rglob("*") if path.is_file())
    (target / "sha256_manifest.txt").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(target).as_posix()}\n" for path in files), encoding="utf-8")
    (target / "readme.txt").write_text(
        "归档原因：原86张图使用英文标题和坐标轴，不符合本项目中文科研绘图要求。\n"
        "本轮仅重新绘图并更新分析，不重新运行Stage10 Formal。\n"
        "归档包含原plots、五个汇总文件、Stage11验证记录和manifest、SHA256清单及原绘图脚本副本。\n"
        "Formal合并CSV未移动、未修改。\n", encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
