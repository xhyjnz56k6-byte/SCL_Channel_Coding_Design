#!/usr/bin/env python3
import shutil,subprocess,sys
from pathlib import Path
def run(c,cwd):print("+"," ".join(c));subprocess.run(c,cwd=cwd,check=True)
def main():
 s=Path(__file__).resolve().parents[1];b=s/"build";r=s/"results"
 if "--clean" in sys.argv and b.exists():shutil.rmtree(b)
 r.mkdir(parents=True,exist_ok=True)
 run(["cmake","-S",str(s),"-B",str(b),"-G","MinGW Makefiles","-DCMAKE_BUILD_TYPE=Release"],s)
 run(["cmake","--build",str(b),"--parallel"],s)
 run([str(b/"stage11_soft_quantization_runner.exe"),str(r)],s)
 run([sys.executable,str(s/"scripts"/"check_stage11.py")],s)
 return 0
if __name__=="__main__":sys.exit(main())
