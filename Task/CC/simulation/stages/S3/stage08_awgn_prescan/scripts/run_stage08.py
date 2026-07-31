#!/usr/bin/env python3
from __future__ import annotations
import shutil,subprocess,sys
from pathlib import Path
def run(c,cwd):print("+"," ".join(c));subprocess.run(c,cwd=cwd,check=True)
def main():
    stage=Path(__file__).resolve().parents[1];build=stage/"build";results=stage/"results"
    if "--clean" in sys.argv and build.exists():shutil.rmtree(build)
    results.mkdir(parents=True,exist_ok=True)
    run(["cmake","-S",str(stage),"-B",str(build),"-G","MinGW Makefiles","-DCMAKE_BUILD_TYPE=Release"],stage)
    run(["cmake","--build",str(build),"--parallel"],stage)
    run([str(build/"stage08_awgn_prescan_runner.exe"),str(results)],stage)
    run([sys.executable,str(stage/"scripts"/"plot_and_check_stage08.py")],stage)
    return 0
if __name__=="__main__":sys.exit(main())
