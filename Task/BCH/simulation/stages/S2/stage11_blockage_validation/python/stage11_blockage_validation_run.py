import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[7];STAGE=Path(__file__).resolve().parents[1]
BUILD=ROOT/"Task/BCH/simulation/build/S2/stage11_blockage_validation";LOGS=STAGE/"logs"
def run(cmd,log):
 r=subprocess.run(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 print(r.stdout,end="");LOGS.mkdir(parents=True,exist_ok=True);(LOGS/log).write_text(r.stdout,encoding="utf-8")
 if r.returncode:raise SystemExit(r.returncode)
run(["cmake","-S",str(STAGE/"cpp"),"-B",str(BUILD),"-G","MinGW Makefiles","-DCMAKE_BUILD_TYPE=Release"],"stage11_blockage_validation_cmake.log")
run(["cmake","--build",str(BUILD),"-j","2"],"stage11_blockage_validation_build.log")
run(["ctest","--test-dir",str(BUILD),"-V","--output-on-failure"],"stage11_blockage_validation_ctest.log")
run(["matlab","-batch",f"addpath('{(STAGE/'matlab').as_posix()}');stage11_blockage_validation_matlab_reference('{STAGE.as_posix()}')"],"stage11_blockage_validation_matlab.log")
run(["python",str(STAGE/"python/stage11_blockage_validation_checker.py")],"stage11_blockage_validation_checker.log")
