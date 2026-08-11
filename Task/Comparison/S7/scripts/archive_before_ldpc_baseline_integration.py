import hashlib
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATE = "20260811"
SUFFIX = "before_ldpc_baseline_integration"
PLOT_IDS = {
    "01_methods_fer",
    "02_methods_ber",
    "03_burst_2_fer",
    "04_burst_5_fer",
    "05_burst_10_fer",
}
PLOT_ASSETS = (
    "figure.png", "figure_data.csv", "plot_manifest.json",
    "plot_validation.json", "readme.txt", "sha256.txt",
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def next_version(parent):
    parent.mkdir(parents=True, exist_ok=True)
    for version in range(1, 100):
        candidate = parent / f"v{version:02d}_{DATE}_{SUFFIX}"
        if not candidate.exists():
            candidate.mkdir()
            return candidate
    raise RuntimeError(f"archive version exhausted: {parent}")


def write_parent_readme(parent, purpose):
    parent.mkdir(parents=True, exist_ok=True)
    readme = parent / "readme.txt"
    if not readme.exists():
        readme.write_text(f"目录用途：{purpose}\n归档规则：旧资产只读保留，不再作为当前正式结果。\n", encoding="utf-8")


def archive_plot(plot_id):
    directory = ROOT / "stage15_scientific_plots" / "results" / "cc" / plot_id
    archive_root = directory / "archive"
    write_parent_readme(archive_root, f"保存 {plot_id} 的历史版本")
    existing = sorted(archive_root.glob(f"v??_{DATE}_{SUFFIX}"))
    if existing and all((existing[-1] / name).is_file() for name in ("figure.png", "figure_data.csv", "plot_manifest.json", "plot_validation.json", "previous_readme.txt", "previous_sha256.txt", "readme.txt", "sha256.txt")):
        return existing[-1]
    target = next_version(archive_root)
    for name in PLOT_ASSETS:
        source = directory / name
        if not source.is_file():
            raise RuntimeError(f"missing current plot asset: {source}")
        destination_name = "previous_readme.txt" if name == "readme.txt" else ("previous_sha256.txt" if name == "sha256.txt" else name)
        shutil.copy2(source, target / destination_name)
    archived_names = ["figure.png", "figure_data.csv", "plot_manifest.json", "plot_validation.json", "previous_readme.txt", "previous_sha256.txt"]
    target.joinpath("readme.txt").write_text(
        "版本：修改前当前正式版本\n"
        f"归档日期：{DATE}\n"
        "归档原因：集成 LDPC 无交织近码率基线前保存旧版\n"
        "修改前是否包含 LDPC：否\n"
        "原图数据来源：S7 Stage11 CC Formal 与历史 CC 无突发 AWGN\n"
        "是否允许用于历史审计：是\n"
        "是否允许继续作为当前正式图：否\n"
        "本轮是否重跑 S7 Formal：否\n"
        "本轮是否重跑 LDPC：否\n"
        "新版本变化：增加 LDPC 无交织近码率 AWGN 参考\n",
        encoding="utf-8",
    )
    hash_names = archived_names + ["readme.txt"]
    target.joinpath("sha256.txt").write_text(
        "".join(f"{sha256(target / name)}  {name}\n" for name in hash_names),
        encoding="utf-8",
    )
    return target


def archive_group(parent, files, purpose):
    archive_root = parent / "archive"
    write_parent_readme(archive_root, purpose)
    target = next_version(archive_root)
    copied = []
    for source in files:
        if source.is_file():
            shutil.copy2(source, target / source.name)
            copied.append(source.name)
    target.joinpath("readme.txt").write_text(
        f"版本：修改前当前正式版本\n归档日期：{DATE}\n归档原因：{purpose}\n"
        "修改前是否包含 LDPC：否（旧 S6 独立参考不计为本轮正式近码率基线）\n"
        "是否允许用于历史审计：是\n是否允许继续作为当前正式结果：否\n"
        "本轮是否重跑 S7 Formal：否\n本轮是否重跑 LDPC：否\n"
        "新版本变化：增加 LDPC 无交织近码率参考及相应 Gate\n",
        encoding="utf-8",
    )
    hash_names = copied + ["readme.txt"]
    target.joinpath("sha256.txt").write_text(
        "".join(f"{sha256(target / name)}  {name}\n" for name in hash_names),
        encoding="utf-8",
    )
    return target


def main():
    plot_archives = [archive_plot(plot_id) for plot_id in sorted(PLOT_IDS)]
    stage15_results = ROOT / "stage15_scientific_plots" / "results"
    stage15_archive = archive_group(
        stage15_results,
        [stage15_results / "plot_inventory.csv", stage15_results / "stage15_validation.json", stage15_results / "readme.txt"],
        "保存 LDPC 基线集成前的 Stage15 总清单、验证与说明",
    )
    root_archive = archive_group(
        ROOT,
        [ROOT / name for name in (
            "S7_metric_summary.csv", "S7_plot_inventory.csv", "S7_result_inventory.csv",
            "S7_source_inventory.csv", "S7_sha256.txt", "S7_manifest.json",
            "S7_validation_report.md", "S7_final_report.md", "S7_known_issues.md", "readme.txt",
        )],
        "保存 LDPC 基线集成前的 S7 顶层表格、清单与最终报告",
    )
    stage16_results = ROOT / "stage16_final_integration" / "results"
    stage16_archive = archive_group(
        stage16_results,
        [stage16_results / "stage16_validation.json", stage16_results / "readme.txt"],
        "保存 LDPC 基线集成前的 Stage16 验证结果",
    )
    print("PASS_S7_LDPC_PREINTEGRATION_ARCHIVE")
    print(f"plotArchives={len(plot_archives)}")
    print(f"stage15Archive={stage15_archive}")
    print(f"rootArchive={root_archive}")
    print(f"stage16Archive={stage16_archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
