#!/usr/bin/env python3
import argparse, pathlib, subprocess, sys

def run(command, cwd): subprocess.run(command, cwd=cwd, check=True)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',required=True); ap.add_argument('--build-dir',required=True); ap.add_argument('--matlab-command',default='matlab'); ap.add_argument('--keep-runtime-output',action='store_true'); a=ap.parse_args()
    root=pathlib.Path(a.repo_root).resolve(); build=pathlib.Path(a.build_dir).resolve(); cpp=build/'cpp_outputs'; mat=build/'matlab_outputs'; check=build/'checker_outputs'
    for d in (cpp,mat,check,build/'plots',build/'logs',build/'temp'): d.mkdir(parents=True,exist_ok=True)
    source=root/'Task/BCH/segmented/current'
    run(['cmake','-G','MinGW Makefiles','-S',str(source),'-B',str(build/'cmake'),'-DCMAKE_BUILD_TYPE=Release'],root)
    run(['cmake','--build',str(build/'cmake')],root)
    run(['ctest','--test-dir',str(build/'cmake'),'--output-on-failure'],root)
    exe=build/'cmake'/'export_bch06_cpp_reference.exe'; run([str(exe),str(cpp)],root)
    mdir=root/'Task/BCH/segmented/matlab'; command=f"addpath('{mdir.as_posix()}'); run_bch06_segmented_matlab_reference('', '{mat.as_posix()}');"
    run([a.matlab_command,'-batch',command],root)
    run([sys.executable,str(root/'Task/BCH/segmented/scripts/check_bch06_segmented_matlab_reference.py'),'--cpp-dir',str(cpp),'--matlab-dir',str(mat),'--output-dir',str(check)],root)
if __name__ == '__main__': main()
