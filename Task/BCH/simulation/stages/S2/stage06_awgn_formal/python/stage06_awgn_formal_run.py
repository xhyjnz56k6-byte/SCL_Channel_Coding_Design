import csv, hashlib, json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[7]; STAGE=Path(__file__).resolve().parents[1]
BUILD=ROOT/"Task/BCH/simulation/build/S2/stage06_awgn_formal"; RESULTS=STAGE/"results"; LOGS=STAGE/"logs"

def run(command,log=None):
    result=subprocess.run(command,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    print(result.stdout,end="")
    if log: log.parent.mkdir(parents=True,exist_ok=True); log.write_text(result.stdout,encoding="utf-8")
    if result.returncode: raise SystemExit(f"command failed ({result.returncode}): {' '.join(map(str,command))}")

def main():
    RESULTS.mkdir(parents=True,exist_ok=True); LOGS.mkdir(parents=True,exist_ok=True)
    config_path=STAGE/"configs/stage06_awgn_formal_config.json"
    config=json.loads(config_path.read_text(encoding="utf-8"))
    points=RESULTS/"stage06_awgn_formal_points.csv"
    with points.open("w",newline="",encoding="utf-8") as stream:
        writer=csv.writer(stream); writer.writerow(["caseId","ebn0Index","ebn0Db"])
        for case_id,grid in config["points"].items():
            for index,value in enumerate(grid): writer.writerow([case_id,index,value])
    config_hash=hashlib.sha256(config_path.read_bytes()).hexdigest()
    git_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    run(["cmake","-S",str(STAGE/"cpp"),"-B",str(BUILD),"-G","MinGW Makefiles","-DCMAKE_BUILD_TYPE=Release"])
    run(["cmake","--build",str(BUILD),"--config","Release","-j","2"])
    run(["ctest","--test-dir",str(BUILD),"-C","Release","--output-on-failure","-V"],
        LOGS/"stage06_awgn_formal_ctest.log")
    run([str(BUILD/"stage06_awgn_formal_runner.exe"),str(points),str(RESULTS),
         str(config["masterSeed"]),config_hash,git_commit],LOGS/"stage06_awgn_formal_runner.log")
    run(["python",str(STAGE/"python/stage06_awgn_formal_plot.py")],LOGS/"stage06_awgn_formal_plot.log")
    run(["python",str(STAGE/"python/stage06_awgn_formal_check.py")],LOGS/"stage06_awgn_formal_check.log")

if __name__=="__main__": main()
