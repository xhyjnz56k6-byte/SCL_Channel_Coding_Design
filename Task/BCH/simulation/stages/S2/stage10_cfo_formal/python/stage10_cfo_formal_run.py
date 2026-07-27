import csv, json, subprocess
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

config=json.loads((STAGE/"configs/stage10_cfo_formal_config.json").read_text(encoding="utf-8"))
RESULTS.mkdir(parents=True,exist_ok=True)
run(["cmake","-S",str(STAGE/"cpp"),"-B",str(BUILD),"-G","MinGW Makefiles","-DCMAKE_BUILD_TYPE=Release"],
    "stage10_cfo_formal_cmake.log")
run(["cmake","--build",str(BUILD),"--config","Release","-j","2"],"stage10_cfo_formal_build.log")
run(["ctest","--test-dir",str(BUILD),"-C","Release","--output-on-failure","-V"],
    "stage10_cfo_formal_ctest.log")
commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
for mode, grids, frames, out_dir in [
    ("trial",{"K200":config["grids"]["K200"][::2],"K300":config["grids"]["K300"][::2]},500,RESULTS/"trial"),
    ("formal",config["grids"],0,RESULTS)]:
    out_dir.mkdir(parents=True,exist_ok=True)
    points=out_dir/f"stage10_cfo_formal_{mode}_points.csv"
    with points.open("w",encoding="utf-8",newline="") as stream:
        w=csv.writer(stream); w.writerow(["caseId","ebn0Index","ebn0Db"])
        for case in CASES:
            for index,db in enumerate(grids["K200" if case.startswith("K200") else "K300"]):
                w.writerow([case,index,db])
    run([str(BUILD/"stage10_cfo_formal_runner.exe"),str(points),str(out_dir),
         str(config["masterSeed"]),commit,mode,str(frames)],
        f"stage10_cfo_formal_{mode}_runner.log")
run(["python",str(STAGE/"python/stage10_cfo_formal_plot.py")],"stage10_cfo_formal_plot.log")
run(["python",str(STAGE/"python/stage10_cfo_formal_checker.py")],"stage10_cfo_formal_checker.log")
