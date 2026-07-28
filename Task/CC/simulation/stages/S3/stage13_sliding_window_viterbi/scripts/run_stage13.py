#!/usr/bin/env python3
import shutil,subprocess,sys
from pathlib import Path
def main():
 s=Path(__file__).resolve().parents[1];b=s/"build";r=s/"results"
 if "--clean" in sys.argv and b.exists():shutil.rmtree(b)
 r.mkdir(exist_ok=True)
 for c in (["cmake","-S",str(s),"-B",str(b),"-G","MinGW Makefiles","-DCMAKE_BUILD_TYPE=Release"],["cmake","--build",str(b),"--parallel"],[str(b/"stage13_runner.exe"),str(r)],[sys.executable,str(s/"scripts"/"check_stage13.py")]):print("+"," ".join(c));subprocess.run(c,cwd=s,check=True)
 return 0
if __name__=="__main__":sys.exit(main())
