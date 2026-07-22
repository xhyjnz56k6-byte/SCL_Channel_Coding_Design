#!/usr/bin/env python3
"""Field-by-field BCH-06 C++/MATLAB CSV checker."""
import argparse, csv, hashlib, json, pathlib, sys

FILES = [
    ("encoder", "cpp_encoder_reference.csv", "matlab_encoder_reference.csv", 2048),
    ("syndrome", "cpp_syndrome_reference.csv", "matlab_syndrome_reference.csv", 15),
    ("no_error_decode", "cpp_no_error_decode.csv", "matlab_no_error_decode.csv", 2048),
    ("single_error_decode", "cpp_single_error_decode.csv", "matlab_single_error_decode.csv", 30720),
]

def read_csv(path):
    raw = path.read_bytes()
    if b"\x00" in raw: raise ValueError(f"NUL byte: {path}")
    text = raw.decode("utf-8-sig")
    rows = list(csv.DictReader(text.splitlines()))
    if not rows and path.name not in ("cpp_syndrome_reference.csv", "matlab_syndrome_reference.csv"):
        raise ValueError(f"empty: {path}")
    return rows, hashlib.sha256(raw).hexdigest(), len(raw)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--cpp-dir",required=True); ap.add_argument("--matlab-dir",required=True); ap.add_argument("--output-dir",required=True); args=ap.parse_args()
    cpp=pathlib.Path(args.cpp_dir); mat=pathlib.Path(args.matlab_dir); out=pathlib.Path(args.output_dir); out.mkdir(parents=True,exist_ok=True)
    result={"files":[],"mismatchTotal":0}
    for label,cn,mn,count in FILES:
        cr,ch,cs=read_csv(cpp/cn); mr,mh,ms=read_csv(mat/mn)
        mismatch=0; first=""
        if len(cr)!=count or len(mr)!=count: mismatch=max(abs(len(cr)-count),abs(len(mr)-count),1); first="row_count"
        elif list(cr[0].keys()) != list(mr[0].keys()): mismatch=1; first="header"
        else:
            for i,(a,b) in enumerate(zip(cr,mr)):
                if a != b: mismatch+=1; first = first or str(i)
        result["files"].append({"name":label,"cppRows":len(cr),"matlabRows":len(mr),"mismatch":mismatch,"firstMismatch":first,"cppSha256":ch,"matlabSha256":mh,"cppBytes":cs,"matlabBytes":ms})
        result["mismatchTotal"] += mismatch
    (out/"cross_check_summary.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    with (out/"cross_check_summary.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["name","cppRows","matlabRows","mismatch","firstMismatch"])
        for x in result["files"]: w.writerow([x["name"],x["cppRows"],x["matlabRows"],x["mismatch"],x["firstMismatch"]])
    if result["mismatchTotal"]: print("BLOCKED_BCH06_CPP_MATLAB_MISMATCH"); return 1
    print("PASS_BCH06_CPP_MATLAB_SEGMENTED_CROSS_CHECK"); return 0
if __name__ == "__main__": sys.exit(main())
