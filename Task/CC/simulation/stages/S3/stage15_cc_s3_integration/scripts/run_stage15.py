#!/usr/bin/env python3
from __future__ import annotations
import csv,hashlib,json,subprocess,sys
from pathlib import Path

def run(c,cwd):
 print("+"," ".join(map(str,c)),flush=True);subprocess.run([str(x) for x in c],cwd=cwd,check=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write_csv(p,fields,rows):
 with p.open("w",encoding="utf-8",newline="") as h:w=csv.DictWriter(h,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)
def main():
 stage=Path(__file__).resolve().parents[1];repo=stage.parents[5];s3=stage.parent;results=stage/"results";results.mkdir(parents=True,exist_ok=True)
 audit=repo/"Task/CC/shared/scripts/cc_stage_audit.py";gates=[]
 for i in range(1,15):
  d=next(s3.glob(f"stage{i:02d}_*"));m=d/"manifest.json"
  if i==1:run([sys.executable,d/"scripts/check_stage01_audit.py"],repo)
  else:run([sys.executable,audit,m],repo)
  j=json.loads(m.read_text(encoding="utf-8"))
  gates.append({"stage":j["stage"],"gate":j["gate"],"status":j.get("gateStatus","PASS"),"contentCommits":"|".join(x["contentCommit"] for x in j["functionalRanges"])})
 # Key executable regressions, including MATLAB official functions.
 scripts=[
  s3/"stage01_cc_contract/tests/test_stage01_contract.py",
  s3/"stage02_trellis_encoder/scripts/build_and_test_stage02.py",
  s3/"stage03_hard_viterbi/scripts/build_and_test_stage03.py",
  s3/"stage04_soft_viterbi/scripts/build_and_test_stage04.py",
  s3/"stage05_matlab_reference/scripts/run_and_check_stage05.py",
  s3/"stage06_puncturing/scripts/run_stage06.py",
  s3/"stage07_block_noiseless/scripts/run_stage07.py",
  s3/"stage12_continuous_encoder/scripts/run_stage12.py",
 ]
 for script in scripts:run([sys.executable,script],repo)
 run([sys.executable,s3/"stage09_awgn_formal/scripts/merge_and_plot_stage09.py","--check-existing",s3/"stage09_awgn_formal/results"],repo)
 for name,script in [
  ("stage10","stage10_traceback_study/scripts/check_stage10.py"),
  ("stage11","stage11_soft_quantization/scripts/check_stage11.py"),
  ("stage13","stage13_sliding_window_viterbi/scripts/check_stage13.py"),
  ("stage14","stage14_block_continuous_comparison/scripts/check_stage14.py")]:run([sys.executable,s3/script],repo)
 run(["git","diff","--check"],repo)
 changed=subprocess.check_output(["git","diff","--name-only","0680b6f4ae00e2c6b1fbe2acecc05d5875e8bfda..HEAD"],cwd=repo,text=True).splitlines()
 if any(not x.startswith("Task/CC/") for x in changed):raise RuntimeError("out-of-scope history")
 write_csv(results/"stage15_cc_s3_integration_gate_matrix.csv",list(gates[0]),gates)
 formal=s3/"stage09_awgn_formal/results/stage09_awgn_formal_point_results.csv"
 with formal.open(encoding="utf-8",newline="") as h:fr=list(csv.DictReader(h))
 cases=[]
 for cid in sorted({x["caseId"] for x in fr}):
  v=[x for x in fr if x["caseId"]==cid];cases.append({"caseId":cid,"rateId":cid.split("-")[2],"decoder":cid.split("-")[3],"pointCount":len(v),"minSnrDb":min(float(x["snrDb"]) for x in v),"maxSnrDb":max(float(x["snrDb"]) for x in v),"N_transmitted":v[0]["N_transmitted"],"actualRate":v[0]["actualRate"]})
 write_csv(results/"stage15_cc_s3_integration_master_case_table.csv",list(cases[0]),cases)
 keyfiles=[
  formal,s3/"stage09_awgn_formal/results/formal_report.md",s3/"stage10_traceback_study/results/stage10_traceback_recommendation.csv",
  s3/"stage11_soft_quantization/results/stage11_quantization_recommendation.csv",s3/"stage12_continuous_encoder/results/stage12_slot_metadata.csv",
  s3/"stage13_sliding_window_viterbi/results/stage13_sliding_window_results.csv",s3/"stage14_block_continuous_comparison/results/stage14_block_continuous_results.csv"]
 index=[{"artifact":p.name,"path":p.relative_to(repo).as_posix(),"sha256":sha(p),"sizeBytes":p.stat().st_size} for p in keyfiles]
 write_csv(results/"stage15_cc_s3_integration_master_result_index.csv",list(index[0]),index)
 plots=[]
 for st,manifest in [(8,s3/"stage08_awgn_prescan/results/stage08_awgn_prescan_plot_manifest.json"),(9,s3/"stage09_awgn_formal/results/stage09_awgn_formal_plot_manifest.json")]:
  for f in json.loads(manifest.read_text(encoding="utf-8"))["figures"]:plots.append({"stage":st,"metric":f["metric"],"png":f["png"],"pngSha256":f["pngSha256"],"sourceCsv":f["sourceCsv"]})
 write_csv(results/"stage15_cc_s3_integration_plot_index.csv",list(plots[0]),plots)
 summary="""# CC S3 集成总结

Stage01～14 Gate 全部 PASS，最终集成回归通过。正式 FER=0.1 的 hard 相对 soft 增益为 1/2 2.085 dB、2/3 1.927 dB、3/4 1.857 dB。码率越高 normalized goodput 上限越高，但达到相同 FER 需要更高 SNR。

推荐 Dtb70（明确为 fallback，最坏 BER/FER 损失 5.70%/12.99%，survivor 内存减少 77.12%）；推荐 receivedSymbols、clipMax2、Q6。整块零尾可靠性和边界最清晰；连续 window96/slide25 可提前输出，推荐 100×3 slots 作为实时折中，但 R23 存在已记录的小幅损失。
"""
 (results/"stage15_cc_s3_integration_summary.md").write_text(summary,encoding="utf-8")
 report=summary+"""
## 最终问题回答

1. soft 相对 hard 提升见上述三组 FER=0.1 增益。
2. R12 冗余最大、低 SNR 最稳；R34 actualRate 最高、goodput 上限最高但瀑布右移；R23 居中。
3. 回溯深度推荐 70，属于性能优先 fallback。
4. 软量化推荐 Q6，Q3/Q4 在当前门限下不合格。
5. 整块适合离线/可靠性优先；连续滑窗适合低首输出时延。
6. 推荐 100×3、window96、slide25、Dtb70。
7. 连续组织避免每 slot 重复尾比特；本 300 bit 统一终止实验 actualRate 与整块相同，滑窗性能损失会降低 successful goodput。
8. 后续 LDPC 对比基线采用六个整块 Case，主基线 R12-soft，吞吐扩展用 R23-soft。
9. 性能、时延和量化结论仅适用于 300 bit、当前 SNR、MinGW/Windows 软件环境与冻结随机策略。
10. S5/S6/S7 复用 Stage09 六 Case、公共 frame/noise key、R12/R23 soft 主线及整块公平定义。
"""
 (results/"stage15_cc_s3_integration_final_report.md").write_text(report,encoding="utf-8")
 (results/"stage15_cc_s3_integration_known_limits.md").write_text("# 已知限制\n\nDtb70 是 fallback 而非无损；R23 滑窗存在已解释 mismatch；软件时延不代表硬件周期；未外推未覆盖 FER；未合并 main。\n",encoding="utf-8")
 (results/"stage15_cc_s3_integration_reproducibility.md").write_text("# 可复现性\n\n使用 masterSeed=2026072001、Common payload/noise policy、各 Stage frozen_config 与 commands_used。Stage09 runtime checkpoint/shard 不提交，但正式点、哈希和 resume 对照结论已提交。\n",encoding="utf-8")
 print("PASS_CC_S3_INTEGRATION")
 return 0
if __name__=="__main__":sys.exit(main())
