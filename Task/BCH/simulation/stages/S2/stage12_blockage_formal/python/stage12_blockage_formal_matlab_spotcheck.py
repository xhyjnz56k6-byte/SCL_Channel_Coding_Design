import csv,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[7];STAGE=Path(__file__).resolve().parents[1];BUILD=ROOT/"Task/BCH/simulation/build/S2/stage12_blockage_formal";R=STAGE/"results"
subprocess.run(["cmake","-S",str(STAGE/"cpp"),"-B",str(BUILD),"-G","MinGW Makefiles","-DCMAKE_BUILD_TYPE=Release"],cwd=ROOT,check=True)
subprocess.run(["cmake","--build",str(BUILD),"-j","2"],cwd=ROOT,check=True)
samples=R/"stage12_blockage_formal_matlab_samples.csv";compare=R/"stage12_blockage_formal_matlab_comparison.csv"
subprocess.run([str(BUILD/"stage12_blockage_formal_runner.exe"),"--spotcheck",str(samples)],cwd=ROOT,check=True)
batch=f"addpath('{(STAGE/'matlab').as_posix()}');stage12_blockage_formal_matlab_spotcheck('{samples.as_posix()}','{compare.as_posix()}','{(ROOT/'Task/BCH/segmented/matlab').as_posix()}')"
r=subprocess.run(["matlab","-batch",batch],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(STAGE/"logs/stage12_blockage_formal_matlab.log").write_text(r.stdout,encoding="utf-8");print(r.stdout,end="");r.check_returncode()
with compare.open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
assert len(rows)==12 and all(x["passed"]=="1" for x in rows)
policies={x["samplePolicy"] for x in rows};assert policies=={"ZERO_RATIO","BOUNDARY_START","RANDOM_START"}
print("PASS_STAGE12_BLOCKAGE_FORMAL_MATLAB_CHECKER")
