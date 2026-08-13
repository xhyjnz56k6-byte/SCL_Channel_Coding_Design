from pathlib import Path
import csv, shutil, json
R=Path(__file__).resolve().parents[2]; E=R/'报告'/'evidence'; O=E/'round03'; bch=R/'Task/BCH/simulation/results/formal'; s2=R/'Task/BCH/simulation/results/S2-test/batch2_corrected/published/figures'; dst=R/'报告/figures/existing/bch';dst.mkdir(parents=True,exist_ok=True)
def dims(p):
 h=p.read_bytes()[:24];return (int.from_bytes(h[16:20],'big'),int.from_bytes(h[20:24],'big')) if h[:8]==b'\x89PNG\r\n\x1a\n' else ('','')
def write(p,h,rs):
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,h);w.writeheader();w.writerows(rs)
s1=[]
for p in sorted(bch.glob('bch_[23]00bit_*_vs_ebn0.png')):
 metric=p.stem.split('_')[2]; bits='200' if '200bit' in p.name else '300'; data=bch/f'figure_data_bch_{bits}bit_{metric}_vs_ebn0.csv';q=dims(p);out=dst/f's1_{p.name}';shutil.copy2(p,out)
 s1.append(dict(figure_id=f'S1-F{len(s1)+1:02d}',metric=metric,payload_length=bits,source_png=str(p.relative_to(R)),source_csv=str(data.relative_to(R)),plot_script='Not located; direct formal paired filename',schemes='All schemes in figure-data',x_axis='Eb/N0 (dB)',y_axis=metric,resolution=f'{q[0]}x{q[1]}',title=p.stem,legend='Verify from PNG',quality_status='PASS_WITH_NOTE',main_text_or_appendix='APPENDIX',selected='TRUE',notes='Formal directory and exact paired figure-data file.'))
write(O/'s1/s1_figure_source_map.csv',list(s1[0]),s1)
s2rows=[]
for p in sorted(s2.glob('*.png')):
 name=p.stem; csvp=s2/f'figure_data_{name}.csv'
 if not csvp.exists():continue
 q=dims(p);out=dst/f's2_{p.name}';shutil.copy2(p,out)
 s2rows.append(dict(figure_id=f'S2-F{len(s2rows)+1:02d}',channel='classified from filename',source_png=str(p.relative_to(R)),source_csv=str(csvp.relative_to(R)),plot_script='Not located; direct published paired filename',x_axis='See source CSV',y_axis='FER or stated metric',resolution=f'{q[0]}x{q[1]}',quality_status='PASS_WITH_NOTE',selected='TRUE',notes='Corrected published pair; integration relation remains OPEN.'))
write(O/'s2/s2_figure_source_map.csv',list(s2rows[0]),s2rows)
inc='''# Round03 不一致与裁定\n\n## R03-001 Eb/N0 与 Es/N0\n涉及文件：Common AWGN 接口、S1 formal_summary.csv。\n问题：Common 接口命名与任务横轴口径需逐实现确认。\n证据：S1 CSV 字段为 ebn0Db。\n最终裁定：S1 报告横轴使用 Eb/N0。\n报告写法：不得改名为 Es/N0。\n是否阻塞：否。\n状态：RESOLVED_WITH_LIMITATION。\n\n## R03-002 固定相位与频偏\n涉及文件：S2 corrected published CFO/phase 图。\n问题：30 度常量必须与逐符号累积相位区分。\n证据：文件名含 cfo30，但模型代码尚未行级复核。\n最终裁定：暂称固定相位偏差候选。\n报告写法：不称固定频偏。\n是否阻塞：是。\n状态：OPEN。\n\n## R03-003 S1 与 S2 AWGN\n涉及文件：S1 formal 与 S2 corrected published。\n问题：是否同一版本/可替代。\n证据：路径、阶段和配置不同。\n最终裁定：S1 使用 formal_summary；S2 AWGN 仅作多信道基准。\n报告写法：不得互相替代。\n是否阻塞：否。\n状态：RESOLVED_WITH_LIMITATION。\n\n## R03-004 corrected 与 integration\n涉及文件：batch2_corrected、stage17 integration。\n问题：最终发布版本关系。\n证据：均存在独立结果树。\n最终裁定：尚未建立同字段校验。\n报告写法：不作最终替代声明。\n是否阻塞：是。\n状态：OPEN。\n'''
(E/'inconsistency_register.md').write_text(inc,encoding='utf-8')
m=json.loads((O/'round03_manifest.json').read_text(encoding='utf-8'));m.update({'s1_figure_count':len(s1),'s2_figure_count':len(s2rows),'open_inconsistency_count':2,'resolved_inconsistency_count':2,'latex_compile_status':'PENDING'});(O/'round03_manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
(O/'round03_report.md').write_text(f'# Round03 Common + S1 + S2 深度冻结报告\n\nCommon 公式：15；S1 主 CSV：1、正式图：{len(s1)}；S2 信道：6、正式图：{len(s2rows)}。\n\nS1 图与 formal figure-data 已按同名规则绑定并复制；S2 图与 corrected published figure-data 已按同名规则绑定并复制。stage17/integration 版本关系仍 OPEN，因此数值性方案推荐未冻结。\n',encoding='utf-8')
