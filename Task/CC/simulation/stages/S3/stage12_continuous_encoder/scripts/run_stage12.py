#!/usr/bin/env python3
import shutil,subprocess,sys
from pathlib import Path
def main():
 s=Path(__file__).resolve().parents[1];b=s/"build"
 if "--clean" in sys.argv and b.exists():shutil.rmtree(b)
 (s/"results").mkdir(exist_ok=True)
 for c in (["cmake","-S",str(s),"-B",str(b),"-G","MinGW Makefiles","-DCMAKE_BUILD_TYPE=Release"],["cmake","--build",str(b),"--parallel"],["ctest","--test-dir",str(b),"--output-on-failure"]):print("+"," ".join(c));subprocess.run(c,cwd=s,check=True)
 return 0
if __name__=="__main__":sys.exit(main())
