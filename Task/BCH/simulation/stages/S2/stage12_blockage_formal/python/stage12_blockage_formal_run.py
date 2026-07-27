import csv,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[7];STAGE=Path(__file__).resolve().parents[1]
BUILD=ROOT/"Task/BCH/simulation/build/S2/stage12_blockage_formal";RESULTS=STAGE/"results";LOGS=STAGE/"logs"
CASES=["K200_S15","K200_M255K207","K200_M511K421","K200_M511K385","K300_S15","K300_M255K207","K300_M511K421","K300_M511K385"]
def run(cmd,log):
 r=subprocess.run(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);print(r.stdout,end="")
 LOGS.mkdir(parents=True,exist_ok=True);(LOGS/log).write_text(r.stdout,encoding="utf-8")
 if r.returncode:raise SystemExit(r.returncode)
c=json.loads((STAGE/"configs/stage12_blockage_formal_config.json").read_text(encoding="utf-8"));RESULTS.mkdir(parents=True,exist_ok=True)
points=RESULTS/"stage12_blockage_formal_points.csv"
with points.open("w",encoding="utf-8",newline="") as f:
 w=csv.writer(f);w.writerow(["experimentType","caseId","ebn0Index","ebn0Db","blockageParameterIndex","requestedBlockageRatio"])
 for case in CASES:
  k="K200" if case.startswith("K200") else "K300";anchor=c["ratioExperiment"][k+"Ebn0Db"]
  for i,rho in enumerate(c["ratioExperiment"]["requestedRatios"]):w.writerow(["RATIO",case,0,anchor,i,rho])
  for i,db in enumerate(c["snrExperiment"][k+"Ebn0Db"]):w.writerow(["SNR",case,i,db,i,c["snrExperiment"]["representativeRatio"]])
run(["cmake","-S",str(STAGE/"cpp"),"-B",str(BUILD),"-G","MinGW Makefiles","-DCMAKE_BUILD_TYPE=Release"],"stage12_blockage_formal_cmake.log")
run(["cmake","--build",str(BUILD),"-j","2"],"stage12_blockage_formal_build.log")
run(["ctest","--test-dir",str(BUILD),"-V","--output-on-failure"],"stage12_blockage_formal_ctest.log")
sha=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
run([str(BUILD/"stage12_blockage_formal_runner.exe"),str(points),str(RESULTS),str(c["masterSeed"]),sha],"stage12_blockage_formal_runner.log")
run(["python",str(STAGE/"python/stage12_blockage_formal_plot.py")],"stage12_blockage_formal_plot.log")
run(["python",str(STAGE/"python/stage12_blockage_formal_checker.py")],"stage12_blockage_formal_checker.log")
