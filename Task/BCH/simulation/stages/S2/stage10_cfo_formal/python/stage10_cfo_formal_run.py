import csv, json, math, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[7]
STAGE=Path(__file__).resolve().parents[1]
BUILD=ROOT/"Task/BCH/simulation/build/S2/stage10_cfo_formal"
RESULTS=STAGE/"results"; LOGS=STAGE/"logs"
CASES=["K200_S15","K200_M255K207","K200_M511K421","K200_M511K385",
       "K300_S15","K300_M255K207","K300_M511K421","K300_M511K385"]

def run(command, log):
    result=subprocess.run(command,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    print(result.stdout,end="")
    LOGS.mkdir(parents=True,exist_ok=True)
    (LOGS/log).write_text(result.stdout,encoding="utf-8")
    if result.returncode: raise SystemExit(result.returncode)

if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip():
    raise SystemExit("BLOCKED_DIRTY_WORKTREE_FORMAL_RUN")

config=json.loads((STAGE/"configs/stage10_cfo_formal_config.json").read_text(encoding="utf-8"))
RESULTS.mkdir(parents=True,exist_ok=True)
run(["cmake","-S",str(STAGE/"cpp"),"-B",str(BUILD),"-G","MinGW Makefiles","-DCMAKE_BUILD_TYPE=Release"],
    "stage10_cfo_formal_cmake.log")
run(["cmake","--build",str(BUILD),"--config","Release","-j","2"],"stage10_cfo_formal_build.log")
run(["ctest","--test-dir",str(BUILD),"-C","Release","--output-on-failure","-V"],
    "stage10_cfo_formal_ctest.log")
commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
with (RESULTS/"stage10_cfo_formal_result_summary.csv").open(encoding="utf-8",newline="") as stream:
    rates={row["caseId"]:float(row["actualRate"]) for row in csv.DictReader(stream)}
grid=config["grids"]["targetSnrDb"]
points=RESULTS/"stage10_cfo_formal_formal_points.csv"
with points.open("w",encoding="utf-8",newline="") as stream:
    w=csv.writer(stream); w.writerow(["caseId","snrIndex","targetSnrDb","ebn0Db"])
    for case in CASES:
        rate=rates[case]
        for index,target in enumerate(grid):
            w.writerow([case,index,target,target-10*math.log10(rate)])
run([str(BUILD/"stage10_cfo_formal_runner.exe"),str(points),str(RESULTS),
     str(config["masterSeed"]),commit,"formal","0"],
    "stage10_cfo_formal_formal_runner.log")
run(["python",str(STAGE/"python/stage10_cfo_formal_plot.py")],"stage10_cfo_formal_plot.log")
run(["python",str(STAGE/"python/stage10_cfo_formal_checker.py")],"stage10_cfo_formal_checker.log")
run(["python",str(STAGE/"python/stage10_cfo_formal_matlab_spotcheck.py")],"stage10_cfo_formal_matlab_runner.log")
