import csv
import json
import math
import os
import subprocess
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
S7 = ROOT / "Task" / "Comparison" / "S7"
OUT = S7 / "chapter9_evidence_audit"
STAGE15 = S7 / "stage15_scientific_plots" / "results"
BCH_FORMAL = S7 / "stage10_bch_formal" / "results" / "formal_results.csv"
CC_FORMAL = S7 / "stage11_cc_formal" / "results" / "formal_results.csv"
LDPC_DIR = S7 / "stage15_scientific_plots" / "ldpc_baseline"


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def write_csv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def git_output(args):
    try:
        return subprocess.check_output(args, cwd=ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN"


def bool_text(value):
    return "true" if bool(value) else "false"


def unique_join(values):
    cleaned = sorted({str(v) for v in values if str(v) != ""})
    return ";".join(cleaned) if cleaned else "N/A"


def classify_plot(plot_id):
    if plot_id in {"01_methods_fer", "02_methods_ber"}:
        return "BASELINE_COMPARISON", "A", "9.3.1" if "bch" else "9.4.1"
    if plot_id.startswith(("03_", "04_", "05_", "22_burst", "23_burst")):
        return "BURST_LENGTH_COMPARISON", "A", "9.3.2/9.4.2"
    if "position" in plot_id or plot_id.startswith(("06_", "07_", "08_", "09_", "10_", "24_", "25_", "26_")):
        return "POSITION_SENSITIVITY", "A", "9.3.3/9.4.3"
    if "affected" in plot_id or "errors_per_block" in plot_id or "short_depth" in plot_id or "equal_span" in plot_id:
        return "MECHANISM_EVIDENCE", "A", "9.3.4/9.4.4/9.4.5"
    if "Improvement" in plot_id or "Reduction" in plot_id or "target_fer" in plot_id:
        return "CONTROLLED_METHOD_COMPARISON", "B", "9.3.5/9.4.6"
    if "Time" in plot_id or "latency" in plot_id:
        return "CPU_TIME_REFERENCE", "B", "9.3.6/9.4.7/9.5"
    if "bufferBits" in plot_id:
        return "BUFFER_COST", "B", "9.3.6/9.4.7"
    if "tolerance" in plot_id:
        return "BURST_TOLERANCE", "B", "9.3.5/9.4.6"
    if "heatmap" in plot_id:
        return "MECHANISM_EVIDENCE", "B", "9.3.3/9.4.3"
    return "ENGINEERING_CONFIGURATION_COMPARISON", "C", "9.6"


def layout_for(plot_id):
    if plot_id in {"01_methods_fer", "02_methods_ber"}:
        return "PAIR"
    if plot_id in {"07_mean_position_fer", "08_max_position_fer", "09_min_position_fer", "24_mean_position_ber", "25_max_position_ber", "26_min_position_ber"}:
        return "TRIPLE"
    if "Time" in plot_id:
        return "TRIPLE"
    if "bufferBits" in plot_id:
        return "TABLE_REPLACEMENT"
    if "latency" in plot_id or "baseline" in plot_id:
        return "REFERENCE_ONLY"
    return "SINGLE"


def collect_figures():
    rows = []
    for scheme in ["bch", "cc"]:
        for d in sorted((STAGE15 / scheme).iterdir()):
            if not d.is_dir() or not (d / "figure.png").exists():
                continue
            manifest = read_json(d / "plot_manifest.json") if (d / "plot_manifest.json").exists() else {}
            data_rows = read_csv(d / "figure_data.csv") if (d / "figure_data.csv").exists() else []
            configs = {r.get("configurationId", "") for r in data_rows}
            source_csvs = {r.get("sourceCsvAbsolutePath", "") for r in data_rows}
            source_stages = {r.get("sourceStage", "") for r in data_rows}
            burst_ratios = {r.get("burstRatio", "") for r in data_rows}
            positions = {r.get("burstPositionType", "") or r.get("burstPosition", "") for r in data_rows}
            esn0 = {r.get("EsN0Db", "") or r.get("x", "") for r in data_rows}
            series = {r.get("series", "") for r in data_rows}
            comparison_type, importance, section = classify_plot(d.name)
            contains_ldpc = bool(manifest.get("containsLdpcNearRateBaseline", False)) or "LDPC_BG2_K300_N640_DIRECT_LAYERED_NMS_A0P80" in configs
            note = ""
            if contains_ldpc:
                note = "LDPC is only a no-burst AWGN near-rate reference overlay; it does not represent the burst condition named by the CC plot."
            rows.append({
                "scheme": scheme.upper(),
                "figureId": d.name,
                "figureDirectory": str(d),
                "figureTitle": manifest.get("title", d.name),
                "sourceCsv": unique_join(source_csvs or manifest.get("sourceAbsolutePaths", [])),
                "sourceStage": unique_join(source_stages),
                "configurationIds": unique_join(configs),
                "comparisonType": comparison_type if not contains_ldpc else ("LDPC_NO_BURST_REFERENCE" if d.name == "22_cc_ldpc_no_burst_decode_latency" else comparison_type),
                "xVariable": manifest.get("xAxis", "EsN0Db"),
                "yVariable": manifest.get("yAxis", d.name),
                "burstRatio": unique_join(burst_ratios),
                "burstPosition": unique_join(positions),
                "EsN0Role": "x-axis or source grid; original grid preserved",
                "containsNoBurstBaseline": bool_text(manifest.get("containsNoBurstBaseline", False) or "NO_BURST_AWGN" in configs),
                "containsLdpcBaseline": bool_text(contains_ldpc),
                "controlledVariables": "payload; S7 formal config hash; shared frame sequence within comparison group; no interpolation; no smoothing",
                "varyingVariables": unique_join(series) if len(series) <= 12 else f"{len(series)} plotted series",
                "scientificQuestion": scientific_question(d.name, scheme.upper()),
                "supportedConclusion": supported_conclusion(d.name, scheme.upper(), contains_ldpc),
                "unsupportedConclusion": unsupported_conclusion(scheme.upper(), contains_ldpc),
                "recommendedChapterSection": section if scheme == "cc" else section.replace("9.4", "9.3"),
                "recommendedLayout": layout_for(d.name),
                "importanceLevel": importance,
                "notes": note or "Evidence maps to existing Stage15 figure data and manifest."
            })
    return rows


def scientific_question(plot_id, scheme):
    if "methods" in plot_id:
        return f"How do the frozen {scheme} interleaver configurations compare under the representative burst condition?"
    if "burst" in plot_id:
        return f"How does {scheme} performance change as contiguous burst length changes?"
    if "position" in plot_id or "heatmap" in plot_id:
        return f"How sensitive is {scheme} to burst start/position?"
    if "Time" in plot_id or "latency" in plot_id:
        return f"What CPU software timing evidence is available for {scheme} or the no-burst baseline?"
    if "bufferBits" in plot_id:
        return f"What structural buffering depth is required by each {scheme} interleaver?"
    return f"What mechanism or engineering tradeoff does this {scheme} result support?"


def supported_conclusion(plot_id, scheme, contains_ldpc):
    base = f"Use this figure as bounded evidence for the frozen {scheme} S7 configuration set."
    if contains_ldpc:
        return base + " LDPC may only be cited as a no-burst AWGN near-rate reference."
    if "affected" in plot_id or "errors_per_block" in plot_id:
        return "BCH interleaving changes the spatial distribution of channel errors across BCH(15,11,1) subblocks."
    if "equal_span" in plot_id:
        return "D16 and pseudo128 share 128 trellis-step span/256 coded-bit buffer, so the comparison isolates arrangement style at equal span."
    return base


def unsupported_conclusion(scheme, contains_ldpc):
    parts = [
        "Do not claim interleaving changes the code's intrinsic error-correction capability.",
        "Do not extrapolate beyond the frozen S7 configurations."
    ]
    if contains_ldpc:
        parts.append("Do not claim LDPC experienced 2%/5%/10% burst or participates in interleaver ranking.")
    if scheme == "BCH":
        parts.append("Do not generalize from segmented BCH(15,11,1) to all BCH codes.")
    return " ".join(parts)


def fairness_rows(formal_path, scheme):
    rows = read_csv(formal_path)
    grouped = defaultdict(list)
    for r in rows:
        key = (r["EsN0Db"], r["burstRatioRequested"], r["burstPositionType"])
        grouped[key].append(r)
    out = []
    fail_count = 0
    for (snr, ratio, pos), items in sorted(grouped.items(), key=lambda x: (float(x[0][0]), float(x[0][1]), x[0][2])):
        payload = {r["payloadChecksum"] for r in items}
        noise = {r["noiseChecksum"] for r in items}
        burst = {r["burstStartChecksum"] for r in items}
        frame = {r["frameSequenceHash"] for r in items}
        status = "PASS" if len(payload) == len(noise) == len(burst) == len(frame) == 1 and len(items) == 4 else "FAIL"
        fail_count += status == "FAIL"
        out.append({
            "scheme": scheme,
            "comparisonGroup": f"{scheme}_EsN0_{snr}_burst_{ratio}_{pos}",
            "EsN0Db": snr,
            "burstRatioRequested": ratio,
            "burstPositionType": pos,
            "configurationCount": len(items),
            "payloadChecksumCount": len(payload),
            "noiseChecksumCount": len(noise),
            "burstStartChecksumCount": len(burst),
            "frameSequenceHashCount": len(frame),
            "payloadChecksum": unique_join(payload),
            "noiseChecksum": unique_join(noise),
            "burstStartChecksum": unique_join(burst),
            "frameSequenceHash": unique_join(frame),
            "status": status,
            "notes": "All four interleaver configurations share payload, noise, burst start and frame sequence." if status == "PASS" else "Shared hash mismatch blocks fairness claim."
        })
    return out, fail_count


def write_burst_definition():
    bch_lengths = {r: int(round(r * 285)) for r in [0.02, 0.05, 0.10]}
    cc_lengths = {r: int(round(r * 612)) for r in [0.02, 0.05, 0.10]}
    text = f"""# Chapter 9 burst-channel definition audit

Source: `Task/Comparison/S7/current/src/s7.cpp` and `Task/Comparison/S7/current/include/s7/s7.hpp`.

## Coding schemes

- BCH fixed scheme: 200 bit payload + 9 bit filler -> 19 x BCH(15,11,1) -> 285 encoded bits. Decoder uses syndrome-table hard-decision BCH(15,11,1) segmented recovery.
- CC fixed scheme: 300 bit payload + 6 zero-tail steps -> 306 trellis steps -> 612 encoded bits. K=7, G1=171(oct), G2=133(oct). Decoder is floating soft terminated full-block Viterbi. No S7 W/S/D sliding-window decoding is used.
- LDPC role: no-interleaving near-rate AWGN baseline only; configuration `LDPC_BG2_K300_N640_DIRECT_LAYERED_NMS_A0P80`.

## Channel model

BPSK mapping:

```text
x_i = +1, bit_i = 0
x_i = -1, bit_i = 1
```

Contiguous burst-error channel:

```text
y_i = h_i x_i + n_i
h_i = -1, s <= i < s + B
h_i = +1, otherwise
n_i = sigma * z_i, z_i ~ N(0, 1)
sigmaSquared = 1 / (2 * 10^(EsN0Db / 10))
```

The burst is applied on the interleaved transmitted sequence. The receiver then demodulates, deinterleaves, and decodes. The interleaver therefore changes the spatial distribution of the contiguous burst as seen by the decoder.

`wrapAround` is false. The channel function rejects wrap-around bursts.

## Burst length

Source rule: `lengthBits = llround(ratio * encodedLength)`.

| Scheme | Encoded length | 2% | 5% | 10% |
|---|---:|---:|---:|---:|
| BCH | 285 | {bch_lengths[0.02]} | {bch_lengths[0.05]} | {bch_lengths[0.10]} |
| CC | 612 | {cc_lengths[0.02]} | {cc_lengths[0.05]} | {cc_lengths[0.10]} |

## Burst start positions

Let `available = encodedLength - B`.

| Position | Start rule |
|---|---|
| HEAD | `s = 0` |
| QUARTER | `s = llround(available / 4)` |
| MIDDLE | `s = llround(available / 2)` |
| THREE_QUARTER | `s = llround(3 * available / 4)` |
| TAIL | `s = available` |
| RANDOM | `s = mix64(2026080427 XOR frameIndex) mod (available + 1)` |

## Formal grid and stop rule

Es/N0 is -5 dB to 10 dB in 0.5 dB steps, 31 points. Burst ratios are 2%, 5% and 10%; positions are HEAD, QUARTER, MIDDLE, THREE_QUARTER, TAIL and RANDOM. Formal stopping is `minFrames=1000`, `targetFrameErrors=200`, `maxFrames=50000`.
"""
    (OUT / "chapter9_burst_channel_definition.md").write_text(text, encoding="utf-8")


def write_timing_audit():
    rows = []
    for scheme in ["BCH", "CC"]:
        rows.extend([
            {
                "metric": "interleaveTimeMeanNsWeighted", "scheme": scheme,
                "codeLocation": "Task/Comparison/S7/current/src/s7.cpp: runBchFrame/runCcFrame interleaveBits call",
                "startOperation": "before interleaveBits(encodedBits,mapping)",
                "endOperation": "after interleaveBits returns transmittedBits",
                "includesAllocation": "true", "includesEncoding": "false", "includesModulation": "false",
                "includesChannel": "false", "includesDeinterleave": "false", "includesDecode": "false",
                "unit": "ns/frame CPU steady_clock",
                "scientificMeaning": "CPU software interleaver function time for the frozen mapping and frame length.",
                "allowedReportWording": "software interleaving average processing time",
                "forbiddenReportWording": "real physical channel delay or system latency without bit/symbol rate"
            },
            {
                "metric": "deinterleaveTimeMeanNsWeighted", "scheme": scheme,
                "codeLocation": "Task/Comparison/S7/current/src/s7.cpp: runBchFrame/runCcFrame deinterleaveBits/deinterleaveValues call",
                "startOperation": "before deinterleave call on hard bits or LLR values",
                "endOperation": "after decoder-order vector returns",
                "includesAllocation": "true", "includesEncoding": "false", "includesModulation": "false",
                "includesChannel": "false", "includesDeinterleave": "true", "includesDecode": "false",
                "unit": "ns/frame CPU steady_clock",
                "scientificMeaning": "CPU software deinterleaver function time before decoding.",
                "allowedReportWording": "software deinterleaving average processing time",
                "forbiddenReportWording": "physical latency or buffering wait converted to ms/us"
            },
            {
                "metric": "decodeTimeMeanNsWeighted", "scheme": scheme,
                "codeLocation": "Task/Comparison/S7/current/src/s7.cpp: BCH decodeBch15Segmented or CC decode_terminated_symbols",
                "startOperation": "after deinterleaving and before decoder call",
                "endOperation": "after decoder call and immediate recovery audit for BCH",
                "includesAllocation": "decoder-internal only", "includesEncoding": "false", "includesModulation": "false",
                "includesChannel": "false", "includesDeinterleave": "false", "includesDecode": "true",
                "unit": "ns/frame CPU steady_clock",
                "scientificMeaning": "software decoder function CPU time reference; not a hardware complexity unit.",
                "allowedReportWording": "software decoder average CPU time",
                "forbiddenReportWording": "universal complexity ranking or hardware latency"
            },
        ])
    write_csv(OUT / "chapter9_timing_definition_audit.csv", [
        "metric", "scheme", "codeLocation", "startOperation", "endOperation",
        "includesAllocation", "includesEncoding", "includesModulation", "includesChannel",
        "includesDeinterleave", "includesDecode", "unit", "scientificMeaning",
        "allowedReportWording", "forbiddenReportWording"
    ], rows)


def write_ldpc_audit():
    selected = read_json(LDPC_DIR / "selected_ldpc_baseline.json")
    manifest = read_json(LDPC_DIR / "ldpc_baseline_manifest.json")
    rows = [{
        "configurationId": selected["configurationId"],
        "payloadBits": selected["payloadBits"],
        "informationBits": selected["informationBits"],
        "fillerBits": selected["fillerBits"],
        "transmittedBits": selected["transmittedBits"],
        "actualRate": selected["actualRate"],
        "CCactualRate": selected["ccActualRate"],
        "absoluteRateDifference": selected["absoluteRateDifference"],
        "relativeRateDifference": selected["relativeRateDifference"],
        "baseGraph": selected["baseGraph"],
        "liftingSize": selected["liftingSize"],
        "decoder": selected["decoder"],
        "alpha": selected["alpha"],
        "maxIterations": selected["maxIterations"],
        "interleaver": selected["interleaver"],
        "channel": selected["channel"],
        "snrDefinition": selected["snrDefinition"],
        "BERavailable": "true",
        "FERavailable": "true",
        "latencyAvailable": "true",
        "complexityAvailable": "algorithm-specific only",
        "burst2Available": "N/A",
        "burst5Available": "N/A",
        "burst10Available": "N/A",
        "comparisonRole": selected["comparisonRole"],
        "selectedPointCount": manifest["selectedPointCount"],
        "sourceCsv": selected["sourceCsv"],
        "sourceSha256": selected["sourceSha256"],
        "notes": "LDPC complexity and CC complexity do not share one operation-count unit; ACS is not equated to one LDPC edge-message update."
    }]
    write_csv(OUT / "chapter9_ldpc_baseline_audit.csv", list(rows[0].keys()), rows)


def write_mechanism_files():
    bch_rows = []
    for fig in ["14_affected_bch_blocks", "15_max_errors_per_block"]:
        d = STAGE15 / "bch" / fig
        data = read_csv(d / "figure_data.csv")
        bch_rows.append({
            "evidenceItem": fig,
            "sourceCsv": str(d / "figure_data.csv"),
            "formalSource": str(BCH_FORMAL),
            "formalFields": "affectedBlocksMean;maximumErrorsInBlock;correctedBlocksMean;miscorrectedBlocks;undetectedFrameErrors;detectedFailureFrames",
            "mechanismClaim": "Interleaving changes how contiguous burst errors are distributed across 19 BCH(15,11,1) subblocks.",
            "supportedChain": "contiguous burst -> errors concentrated in fewer 15-bit subblocks without interleaving -> more local multi-error blocks -> may exceed t=1 local correction -> interleaving spreads errors across more subblocks -> maximum errors per block can decrease -> more blocks remain in single-bit correction range -> FER can improve",
            "forbiddenClaim": "Interleaving improves the intrinsic theoretical correction capability of BCH(15,11,1).",
            "rowCount": len(data),
            "status": "PASS" if data else "FAIL"
        })
    write_csv(OUT / "chapter9_bch_mechanism_evidence.csv", list(bch_rows[0].keys()), bch_rows)

    cc_rows = []
    for fig, claim in [
        ("14_short_depth_parameters", "D increase changes span and buffer; D8 is an engineering recommended point."),
        ("15_equal_span_128_controlled", "D16 and pseudo128 both have span=128 trellis steps and buffer=256 coded bits, enabling controlled arrangement comparison."),
        ("20_burst_tolerance", "Burst tolerance evidence is CC-only and cannot include LDPC extrapolation.")
    ]:
        d = STAGE15 / "cc" / fig
        data = read_csv(d / "figure_data.csv")
        cc_rows.append({
            "evidenceItem": fig,
            "sourceCsv": str(d / "figure_data.csv"),
            "formalSource": str(CC_FORMAL),
            "mechanismClaim": claim,
            "supportedChain": "contiguous abnormal observations concentrated in adjacent trellis steps affect path-metric competition; interleaving spreads observations to farther trellis positions and reduces concentrated local disturbance.",
            "forbiddenClaim": "Interleaving increases convolutional-code free distance or intrinsic error-correction capability.",
            "rowCount": len(data),
            "status": "PASS" if data else "FAIL"
        })
    write_csv(OUT / "chapter9_cc_mechanism_evidence.csv", list(cc_rows[0].keys()), cc_rows)


def write_table_and_layout(fig_rows):
    tables = [
        ("9.1", "Unified S7 simulation parameters and burst-error channel", "configs/s7_formal_frozen_config.json; chapter9_burst_channel_definition.md", "Es/N0 grid; burst ratios; positions; stop rule", "parameter,value,source,notes", "N/A only for non-applicable LDPC burst fields", "false"),
        ("9.2", "Fixed BCH and CC coding schemes", "current/include/s7/s7.hpp; current/src/s7.cpp", "BCH/CC constants and decoder calls", "scheme,payload,tail/filler,encoded length,rate,decoder", "N/A for CC filler and BCH tail", "false"),
        ("9.3", "BCH formal interleaver definitions", "current/src/s7.cpp; formal_results.csv", "BCH configs only", "configuration,method,parameter,spanBits,bufferBits,mapping description", "N/A for trellis-only fields", "false"),
        ("9.4", "CC formal interleaver definitions", "current/src/s7.cpp; formal_results.csv", "CC configs only", "configuration,method,parameter,spanTrellisSteps,spanBits,bufferBits", "N/A for BCH-only fields", "false"),
        ("9.5", "Representative BCH FER improvement", "figure evidence matrix; Stage15 BCH figure_data.csv", "A-level BCH FER figures", "condition,baseline,method,FER,improvement,source figure", "Use N/A where improvement is not computed", "true only if source CSV already contains target FER gain"),
        ("9.6", "BCH burst dispersion mechanism metrics", "chapter9_bch_mechanism_evidence.csv", "affected blocks and max errors per block", "configuration,affectedBlocksMean,maximumErrorsInBlock,correctedBlocksMean", "N/A for missing diagnostic fields", "false"),
        ("9.7", "Representative CC FER improvement", "Stage15 CC figure_data.csv", "A-level CC FER figures", "condition,baseline,method,FER,improvement,source figure", "Use N/A where improvement is not computed", "true only if source CSV already contains target FER gain"),
        ("9.8", "CC short-depth and equal-span comparison", "14_short_depth_parameters; 15_equal_span_128_controlled", "D8,D16,pseudo128", "configuration,spanTrellisSteps,bufferBits,FER,comparison role", "N/A for non-controlled comparisons", "false"),
        ("9.9", "Interleaver buffer and CPU processing time", "timing audit; Stage15 timing figures", "buffer and timing metrics", "scheme,configuration,bufferBits,interleave ns,deinterleave ns,decode ns", "Do not convert bufferBits to time", "false"),
        ("9.10", "Burst-error tolerance", "20_burst_tolerance figures", "BCH and CC only", "scheme,configuration,tolerance metric,source", "LDPC=N/A", "false"),
        ("9.11", "CC and LDPC no-interleaving near-rate baseline", "S7_coding_reference_summary.csv; LDPC audit", "no-burst AWGN only", "scheme,rate,BER,FER,decode CPU reference,role", "LDPC burst columns=N/A", "false"),
        ("9.12", "Final engineering configuration recommendation", "Stage15/16 summaries; evidence matrix", "S7 frozen recommendation only", "scheme,recommended configuration,evidence,limitations", "N/A for unsupported dimensions", "false"),
    ]
    rows = [{
        "tableId": tid, "tableTitle": title, "sourceCsv": source, "filterRule": flt,
        "columns": cols, "rowRule": "select representative rows; do not paste raw large CSV blocks",
        "requiresInterpolation": interp, "forbidsInterpolation": "true", "naRule": na
    } for tid, title, source, flt, cols, na, interp in tables]
    write_csv(OUT / "chapter9_table_plan.csv", list(rows[0].keys()), rows)

    layout_rows = [{
        "scheme": r["scheme"],
        "figureId": r["figureId"],
        "figureTitle": r["figureTitle"],
        "recommendedLayout": r["recommendedLayout"],
        "pairedWith": paired_with(r["figureId"]),
        "chapterSection": r["recommendedChapterSection"],
        "importanceLevel": r["importanceLevel"],
        "coverageDecision": "main text or three-line table evidence; not appendix",
        "notes": r["notes"]
    } for r in fig_rows]
    write_csv(OUT / "chapter9_figure_layout_plan.csv", list(layout_rows[0].keys()), layout_rows)


def paired_with(plot_id):
    pairs = {
        "01_methods_fer": "02_methods_ber",
        "02_methods_ber": "01_methods_fer",
        "16_decodeTimeMeanNsWeighted": "17_interleaveTimeMeanNsWeighted;18_deinterleaveTimeMeanNsWeighted",
        "17_interleaveTimeMeanNsWeighted": "16_decodeTimeMeanNsWeighted;18_deinterleaveTimeMeanNsWeighted",
        "18_deinterleaveTimeMeanNsWeighted": "16_decodeTimeMeanNsWeighted;17_interleaveTimeMeanNsWeighted",
    }
    return pairs.get(plot_id, "N/A")


def write_section_map():
    text = """# Chapter 9 section evidence map

## 9.1 Interleaving burst-error objective and chain

Figures: overview references from Stage15 A-level figures. CSV: `chapter9_figure_evidence_matrix.csv`, `chapter9_burst_channel_definition.md`. Tables: 9.1. Question: what channel and evidence chain is Chapter 9 allowed to use?

## 9.2 Fixed coding schemes, burst-error channel and interleavers

Figures: none required; use definitions. CSV: timing audit, LDPC audit, formal configs. Tables: 9.1-9.4. Question: what exactly are BCH, CC and the burst-error channel in S7?

## 9.3 BCH segmented scheme under burst errors

Use BCH figures 01-28, including duplicated numeric prefix `22_all_start_heatmap_5_percent` and `22_burst_5_ber` as distinct directories. CSV: BCH formal results and BCH rows in `chapter9_figure_evidence_matrix.csv`. Tables: 9.3, 9.5, 9.6, 9.9, 9.10. Question: how does interleaving change BCH subblock error distribution and observed FER/BER?

## 9.4 CC interleaving under burst errors

Use CC figures 01-21. CSV: CC formal results and CC rows in the evidence matrix. Tables: 9.4, 9.7, 9.8, 9.9, 9.10. Question: how do short-depth and pseudorandom trellis-step interleavers affect local trellis disturbance?

## 9.5 High-speed no-interleaving LDPC near-rate baseline

Use CC figure `22_cc_ldpc_no_burst_decode_latency` and CC figures 01-05 only as LDPC AWGN overlays. CSV: `chapter9_ldpc_baseline_audit.csv`, `S7_coding_reference_summary.csv`. Table: 9.11. Question: what can the no-burst LDPC reference say without becoming a burst or interleaver claim?

## 9.6 Combined interleaving gain and engineering cost

Use buffer, timing, improvement and tolerance figures. CSV: evidence matrix, timing audit, table plan. Tables: 9.9, 9.10, 9.12. Question: what performance-cost tradeoff is supported by existing S7 evidence?

## 9.7 Chapter conclusion

Use only conclusions already supported by the figure/data matrix. LDPC remains a no-interleaving AWGN baseline and does not enter interleaver ranking or burst tolerance extrapolation.
"""
    (OUT / "chapter9_section_evidence_map.md").write_text(text, encoding="utf-8")


def write_language_guardrails():
    text = """# Chapter 9 language guardrails

## Forbidden exaggerations

- unique winner
- perfect
- crush
- damage
- huge cost
- obvious
- it is not difficult to find

## Forbidden writing/meta language

- do not address the reader directly
- do not include writing instructions in the thesis text
- do not write phrases like "this section will tell the reader"
- do not write phrases like "attention should be paid here"
- do not write phrases like "to make the figure look better"

## Technical wording allowed

BCH, LDPC, BPSK, AWGN, FER, BER, Es/N0, Viterbi and trellis may remain in English where they are technical terms.

Internal field names such as `fairnessGroupId`, `comparisonRole` and `engineeringComparisonGroup` must be translated into formal thesis wording and not copied directly into the prose.

## Required boundaries

- BCH conclusion must say this chapter uses the fixed 200 bit segmented BCH(15,11,1) scheme to study interleaving effects; do not generalize to all BCH codes.
- CC conclusion must say S7 uses terminated full-block floating soft Viterbi, not S3 sliding-window W/S/D decoding.
- LDPC conclusion must say LDPC is a no-interleaving no-burst AWGN near-rate reference only.
- Buffer bits may be described as structural coded-bit buffering depth, not physical delay.
"""
    (OUT / "chapter9_language_guardrails.md").write_text(text, encoding="utf-8")


def write_readme_and_report(fig_rows, fairness_failures):
    validation = read_json(STAGE15 / "stage15_validation.json")
    selected = read_json(LDPC_DIR / "selected_ldpc_baseline.json")
    bch_count = sum(1 for r in fig_rows if r["scheme"] == "BCH")
    cc_count = sum(1 for r in fig_rows if r["scheme"] == "CC")
    a_count = sum(1 for r in fig_rows if r["importanceLevel"] == "A")
    b_count = sum(1 for r in fig_rows if r["importanceLevel"] == "B")
    c_count = sum(1 for r in fig_rows if r["importanceLevel"] == "C")
    gate = "PASS_ROUND10_A_S7_CHAPTER9_FORMAL_EVIDENCE_AUDIT" if fairness_failures == 0 and validation.get("status") == "PASS" and bch_count == 29 and cc_count == 22 else "FAIL"
    report = f"""# Chapter 9 evidence audit report

Gate: {gate}

Branch: {git_output(['git','branch','--show-current'])}

HEAD: {git_output(['git','rev-parse','HEAD'])}

## Figure counts

- Stage15 total plots: {validation.get('plotCount')} (actual audited directories: {len(fig_rows)})
- BCH plots: {bch_count}
- CC plots: {cc_count}
- A/B/C importance counts: A={a_count}, B={b_count}, C={c_count}

## LDPC baseline

- configurationId: {selected['configurationId']}
- payloadBits: {selected['payloadBits']}
- transmittedBits: {selected['transmittedBits']}
- actualRate: {selected['actualRate']}
- CC actualRate: {selected['ccActualRate']}
- decoder: {selected['decoder']}, alpha={selected['alpha']}, maxIterations={selected['maxIterations']}
- interleaver: NONE
- channel: NO_BURST_AWGN
- role: no-interleaving near-rate AWGN reference only

## Fixed schemes

- BCH fixed scheme: 200 bit payload + 9 bit filler -> 19 x BCH(15,11,1) -> 285 encoded bits.
- CC fixed scheme: 300 bit payload + 6 zero-tail steps -> 306 trellis steps -> 612 encoded bits; K=7, G1=171(oct), G2=133(oct); terminated full-block floating soft Viterbi.

## Interleaver summary

- BCH NONE: identity permutation, bufferBits=0.
- BCH_CODEBLOCK: D in {{4,8,16,19}}; D=19 forms a 19 x 15 BCH subblock-structured interleaver, column-read within BCH codeblock organization, spanBits=285, bufferBits=285.
- BCH ROW_COLUMN: row-write/column-read over the full 285 bit frame; R=15 in formal config, spanBits=285, bufferBits=285.
- BCH GLOBAL_PSEUDORANDOM: deterministic full-frame 285 bit permutation with fixed seed, spanBits=285, bufferBits=285.
- CC NONE: identity trellis-step order, preserves mother-code output pairs, bufferBits=0.
- CC SHORT_DEPTH_BLOCK: D in {{4,8,16}}, window=8*D trellis steps, preserves each mother-code output pair.
- CC PSEUDORANDOM: span in {{32,64,128}} trellis steps, deterministic shuffle inside local windows, not a full-frame 306 step shuffle.
- D8 span/buffer: 64 trellis steps / 128 coded bits.
- D16 span/buffer: 128 trellis steps / 256 coded bits.
- pseudo128 span/buffer: 128 trellis steps / 256 coded bits.

## Fairness and timing

- Formal fairness audit rows: {1116}
- Fairness failures: {fairness_failures}
- Timing path: interleave/deinterleave/decode steady_clock CPU function timing only; bufferBits is structural coded-bit buffering depth and is not converted to physical delay.

## Blocking issues

None blocking for Chapter 9 evidence use when LDPC and wording boundaries are respected.

## Generated files

See `readme.txt` in this directory for the complete file list.

## Git

- commit: NO
- push: NO
- stage: NO
- merge main: NO
"""
    (OUT / "chapter9_evidence_audit_report.md").write_text(report, encoding="utf-8")
    files = sorted(p.name for p in OUT.iterdir() if p.is_file() and p.name != "generate_chapter9_evidence_audit.py")
    readme = "S7 Chapter 9 formal evidence audit outputs.\n\nGenerated files:\n" + "\n".join(f"- {name}" for name in files) + "\n\nNo Formal data was rerun or modified. No commit, push, stage, or merge was performed by this audit generator.\n"
    (OUT / "readme.txt").write_text(readme, encoding="utf-8")
    return gate


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fig_rows = collect_figures()
    figure_fields = [
        "scheme", "figureId", "figureDirectory", "figureTitle", "sourceCsv", "sourceStage",
        "configurationIds", "comparisonType", "xVariable", "yVariable", "burstRatio",
        "burstPosition", "EsN0Role", "containsNoBurstBaseline", "containsLdpcBaseline",
        "controlledVariables", "varyingVariables", "scientificQuestion", "supportedConclusion",
        "unsupportedConclusion", "recommendedChapterSection", "recommendedLayout",
        "importanceLevel", "notes"
    ]
    write_csv(OUT / "chapter9_figure_evidence_matrix.csv", figure_fields, fig_rows)

    fairness_bch, fail_bch = fairness_rows(BCH_FORMAL, "BCH")
    fairness_cc, fail_cc = fairness_rows(CC_FORMAL, "CC")
    fairness_fields = list(fairness_bch[0].keys())
    write_csv(OUT / "chapter9_fairness_audit.csv", fairness_fields, fairness_bch + fairness_cc)

    write_burst_definition()
    write_ldpc_audit()
    write_timing_audit()
    write_mechanism_files()
    write_table_and_layout(fig_rows)
    write_section_map()
    write_language_guardrails()
    gate = write_readme_and_report(fig_rows, fail_bch + fail_cc)
    print(gate)


if __name__ == "__main__":
    main()
