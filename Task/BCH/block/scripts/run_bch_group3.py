#!/usr/bin/env python3
import argparse, pathlib, subprocess, sys

def run(command, root):
    subprocess.run(command, cwd=root, check=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--stage',choices=['bch07','bch08','bch09','bch10'])
    ap.add_argument('--all',action='store_true')
    ap.add_argument('--skip-matlab',action='store_true')
    ap.add_argument('--matlab-command',default='D:/Apps/Matlab/bin/matlab.exe')
    ap.add_argument('--build-dir',default='Task/BCH/block/build/group3')
    args=ap.parse_args()
    if not args.all and not args.stage: ap.error('select --stage or --all')
    root=pathlib.Path(__file__).resolve().parents[4]; build=root/args.build_dir; ref=build/'reference'; ref.mkdir(parents=True,exist_ok=True)
    run(['cmake','-G','MinGW Makefiles','-S','Task/BCH/block/current','-B',str(build)],root)
    run(['cmake','--build',str(build),'-j','2'],root); run(['ctest','--test-dir',str(build),'--output-on-failure'],root)
    run([str(build/'export_bch_block_reference.exe'),str(ref/'cpp_bch07.csv')],root)
    run([str(build/'export_bch_block_detail.exe'),str(ref/'cpp_detail.csv')],root)
    run([str(build/'export_bch_block_pool_encoder.exe'),'Task/Common/build/stage04/real_pool_runs/smoke/frames/k200/manifest.json','Task/Common/build/stage04/real_pool_runs/smoke/frames/k300/manifest.json',str(ref/'cpp_pool_encoder.csv')],root)
    run([str(build/'export_bch_block_gf_detail.exe'),str(ref/'cpp_gf_detail.csv')],root)
    run([str(build/'export_bch_block_illegal.exe'),str(ref/'cpp_illegal.csv')],root)
    if args.skip_matlab: return
    mdir='Task/BCH/block/matlab'
    command=(f"addpath('{mdir}'); run_bch_group3_reference('{ref.as_posix()}/matlab_bch07.csv','{ref.as_posix()}/matlab_detail.csv'); "
             f"run_bch_group3_toolbox_reference('{ref.as_posix()}/matlab_toolbox_bch07.csv'); "
             f"run_bch_group3_pool_encoder('Task/Common/build/stage04/real_pool_runs/smoke/frames/k200/manifest.json','Task/Common/build/stage04/real_pool_runs/smoke/frames/k300/manifest.json','{ref.as_posix()}/matlab_pool_encoder.csv'); "
             f"run_bch_group3_gf_detail('{ref.as_posix()}/matlab_gf_detail.csv'); run_bch_group3_illegal_reference('{ref.as_posix()}/matlab_illegal.csv'); "
             f"run_bch_group3_toolbox_codec('Task/Common/build/stage04/real_pool_runs/smoke/frames/k200/manifest.json','Task/Common/build/stage04/real_pool_runs/smoke/frames/k300/manifest.json','{ref.as_posix()}/matlab_toolbox_codec.csv');")
    run([args.matlab_command,'-batch',command],root)
    for script,files in [('check_bch07_reference.py',['cpp_bch07.csv','matlab_bch07.csv']),('check_bch07_toolbox.py',['cpp_bch07.csv','matlab_toolbox_bch07.csv']),('check_bch07_gf_detail.py',['cpp_gf_detail.csv','matlab_gf_detail.csv']),('check_bch08_pool_encoder.py',['cpp_pool_encoder.csv','matlab_pool_encoder.csv']),('check_bch10_detail.py',['cpp_detail.csv','matlab_detail.csv']),('check_bch10_illegal.py',['cpp_illegal.csv','matlab_illegal.csv']),('check_bch10_toolbox_codec.py',['matlab_toolbox_codec.csv'])]:
        run([sys.executable,'Task/BCH/block/scripts/'+script,*[str(ref/x) for x in files]],root)
if __name__=='__main__': main()
