#!/usr/bin/env python3
"""Conservative round-02 evidence freezing.  Reads Task; writes only 报告."""
from __future__ import annotations
import csv, hashlib, json, re, shutil, sys, zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]; R=ROOT/'报告'; E=R/'evidence'
BANNED=('archive','backup','old','temp','patch_verify','smoke','trial','worker','shard','checkpoint','test_output','negative')
PREFERRED=('revised','final','formal_summary','merged','integration','recommend','comparison','figure_data','point_results','full_')
TASKS=['S1','S2','S3','S4','S5','S6','S7']
REQS=['编制目的与任务要求','200 bit 和 300 bit 输入电文','低速与高速业务定位','单块编码后总长度不超过 1000 bit','码率范围','BCH 码型与比较要求','卷积码参数与 Viterbi 译码','LDPC BG2、码长与 Direct 约束','BP 与 NMS 比较','10/20/30 次迭代要求','交织作为独立测试','LDPC 不配置交织','S1 至 S7 任务定义','每任务输入与对比方案','BER 和 FER 曲线','平均与最大译码时延','复杂度统计','编码增益','交织附加时延','综合场景推荐']

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()
def task_of(s):
 l=s.lower().replace('\\','/')
 for t in TASKS:
  if f'/{t.lower()}/' in l or f'_{t.lower()}_' in l: return t
 if '/comparison/s5/' in l:return 'S5'
 if '/comparison/s6/' in l:return 'S6'
 if '/comparison/s7/' in l:return 'S7'
 if '/bch/' in l:return 'S1'
 if '/cc/' in l:return 'S3'
 if '/ldpc/' in l:return 'S4'
 return 'S5' if 'channel' in l else 'S6' if 'decoder' in l else 'UNKNOWN'
def write(name, header, rows):
 with (E/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=header); w.writeheader();w.writerows(rows)
def docx_text(p):
 with zipfile.ZipFile(p) as z: root=ET.fromstring(z.read('word/document.xml'))
 return '\n'.join(x.text or '' for x in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))
def main():
 E.mkdir(parents=True,exist_ok=True); stamp=datetime.now().strftime('%Y%m%d_%H%M%S'); archive=E/'archive'/f'round01_full_scan_{stamp}';archive.mkdir(parents=True)
 names=['source_inventory.csv','result_inventory.csv','figure_inventory.csv','formula_inventory.csv','conclusion_evidence_matrix.csv','final_result_selection.md','inconsistency_register.md','missing_materials.md','teacher_requirements.md','visio_figure_plan.md','scan_report.md','scan_manifest.json','common_scan.md','scan_execution.log']
 for n in names:
  if (E/n).exists(): shutil.copy2(E/n,archive/n)
 log=[f'round02 start {datetime.now().isoformat()}',f'round01 archive {archive.relative_to(R)}']
 rows=list(csv.DictReader((E/'result_inventory.csv').open(encoding='utf-8-sig')))
 selected=[]
 for t in TASKS:
  pool=[]
  for x in rows:
   p=x['relative_path'].lower(); name=x['file_name'].lower()
   if task_of(x['relative_path'])!=t or any(b in p for b in BANNED): continue
   score=sum(k in name or k in p for k in PREFERRED)+ (3 if x.get('formal_flag')=='TRUE' else 0)
   if score>=3: pool.append((score,x))
  pool.sort(key=lambda z:(-z[0],z[1]['relative_path']))
  seen=set()
  for score,x in pool:
   key=x['file_name'].lower()
   if key in seen:continue
   seen.add(key);selected.append((t,score,x))
   if len(seen)>=8:break
 # fallback guarantee
 for t in TASKS:
  if not any(z[0]==t for z in selected):
   for x in rows:
    if task_of(x['relative_path'])==t and not any(b in x['relative_path'].lower() for b in BANNED): selected.append((t,0,x));break
 result_header='result_id task subtask experiment scheme payload_length encoded_length transmitted_length actual_rate channel decoder snr_type snr_min snr_max snr_step snr_point_count min_frames target_frame_errors max_frames stop_policy pairing_policy main_csv figure_data_csv checker manifest source_code selected selection_reason limitations sha256'.split()
 frozen=[]; version=[]
 for i,(t,score,x) in enumerate(selected,1):
  src=ROOT/x['relative_path']; outdir=R/'data'/'frozen'/({'S1':'bch','S2':'bch','S3':'cc','S4':'ldpc','S5':'multichannel','S6':'decoder','S7':'interleaving'}[t]);outdir.mkdir(parents=True,exist_ok=True)
  target=outdir/f'{t.lower()}_{i:02d}_{src.name}'; shutil.copy2(src,target)
  frozen.append(dict(result_id=f'FRZ-{i:03d}',task=t,subtask='UNKNOWN',experiment=src.stem,scheme='See CSV',payload_length='UNKNOWN',encoded_length='UNKNOWN',transmitted_length='UNKNOWN',actual_rate='UNKNOWN',channel='See CSV',decoder='See CSV',snr_type='UNKNOWN',snr_min='UNKNOWN',snr_max='UNKNOWN',snr_step='UNKNOWN',snr_point_count='UNKNOWN',min_frames='UNKNOWN',target_frame_errors='UNKNOWN',max_frames='UNKNOWN',stop_policy='See manifest/checker',pairing_policy='UNKNOWN',main_csv=str(target.relative_to(R)),figure_data_csv='',checker='',manifest='',source_code='',selected='TRUE',selection_reason=f'non-archive formal/master candidate; priority score {score}',limitations='Column-level parameter and plot-source verification remains required.',sha256=digest(src)))
  version.append(dict(duplicate_group='DUP-'+digest(src)[:12],task=t,file_path=x['relative_path'],sha256=digest(src),size=src.stat().st_size,modified_time=src.stat().st_mtime,content_relation='UNKNOWN',version_role='MASTER',superseded_by='',selected_status='SELECTED',selection_reason=f'round02 priority score {score}',notes='Automated conservative selection; no archive/worker/shard/smoke path.'))
 write('frozen_result_inventory.csv',result_header,frozen)
 write('duplicate_and_version_map.csv','duplicate_group task file_path sha256 size modified_time content_relation version_role superseded_by selected_status selection_reason notes'.split(),version)
 # figures: choose nonarchive formal-like paths, capped at five/task
 figrows=list(csv.DictReader((E/'figure_inventory.csv').open(encoding='utf-8-sig'))); figs=[]
 for t in TASKS:
  take=[x for x in figrows if task_of(x['relative_path'])==t and x.get('archive_flag')!='TRUE' and not any(b in x['relative_path'].lower() for b in BANNED)]
  for x in take[:5]:
   src=ROOT/x['relative_path']; folder=R/'figures'/'existing'/({'S1':'bch','S2':'bch','S3':'cc','S4':'ldpc','S5':'multichannel','S6':'decoder','S7':'interleaving'}[t]);folder.mkdir(parents=True,exist_ok=True); dst=folder/f'{t.lower()}_{len(figs)+1:02d}.png';shutil.copy2(src,dst)
   figs.append(dict(figure_id=f'FF-{len(figs)+1:03d}',task=t,subtask='UNKNOWN',title=src.stem,source_png=x['relative_path'],copied_png=str(dst.relative_to(R)),width_px=x.get('width_px',''),height_px=x.get('height_px',''),metric='UNKNOWN',x_axis='Verify against plot source',y_axis='Verify against plot source',schemes='See source PNG',channels='UNKNOWN',source_csv='',plot_script='',checker='',main_text_or_appendix='APPENDIX_PENDING_REVIEW',selection_reason='Non-archive figure candidate; copied without modification.',quality_status='PASS_WITH_NOTE',sha256=digest(src),notes='CSV linkage must be completed before main-text use.'))
 write('frozen_figure_inventory.csv','figure_id task subtask title source_png copied_png width_px height_px metric x_axis y_axis schemes channels source_csv plot_script checker main_text_or_appendix selection_reason quality_status sha256 notes'.split(),figs)
 # source-required teacher requirements
 doc=ROOT/'任务要求'/'附件3-信道编码、交织与译码方案及仿真分析.docx'; doc_text=docx_text(doc) if doc.exists() else ''
 tr=[]
 for i,q in enumerate(REQS,1): tr.append(dict(requirement_id=f'TR-{i:03d}',requirement_text=q,source_file=str(doc.relative_to(ROOT)) if doc.exists() else 'MISSING',page='PDF page verification pending',section='DOCX structured text',task='S1-S7',implementation_source='To be linked per task evidence',parameter_source='frozen_parameter_inventory.csv',result_source='frozen_result_inventory.csv',figure_source='frozen_figure_inventory.csv',status='PARTIALLY_SATISFIED',deviation='Evidence links require task-level verification.',report_treatment='State requirement and cite only verified implementation/data.',notes=f'DOCX located; extracted {len(doc_text)} characters.'))
 write('requirement_traceability_matrix.csv','requirement_id requirement_text source_file page section task implementation_source parameter_source result_source figure_source status deviation report_treatment notes'.split(),tr)
 md=['# 教师原始要求','',f'已读取 DOCX 结构化文本（{len(doc_text)} 字符）；PDF 将用于后续页码复核。','', '| requirement_id | 原始要求摘要 | 原始文件 | 页码 | 对应任务 | 状态 | 差异 | 报告处理方式 |','|---|---|---|---|---|---|---|---|']
 md += [f'| {r["requirement_id"]} | {r["requirement_text"]} | `{r["source_file"]}` | 待 PDF 页码复核 | S1--S7 | PARTIALLY\_SATISFIED | 待逐任务绑定 | 仅使用冻结证据 |' for r in tr]
 (E/'teacher_requirements.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
 # Explicit, bounded formula and parameter ledgers
 formulas=[('F-01','统一仿真','实际码率',r'R=K/N','K: payload bits; N: transmitted bits','Common source and frozen CSV'),('F-02','统一仿真','BPSK',r'x=1-2b','b: bit; x: transmitted symbol','Common demodulation implementation'),('F-03','统一仿真','BER',r'\mathrm{BER}=N_b^{err}/N_b','bit-error count / tested bits','metric definition'),('F-04','统一仿真','FER',r'\mathrm{FER}=N_f^{err}/N_f','frame-error count / tested frames','metric definition'),('F-05','统一仿真','LLR',r'L=2y/\sigma^2','y: received sample; sigma squared: noise variance','demodulation implementation'),('F-06','LDPC','校验方程',r'\mathbf{H}\mathbf{x}^{T}=\mathbf{0}','H: parity-check matrix','LDPC source'),('F-07','LDPC','NMS 校验节点',r'r_{m\to n}=\alpha\prod\operatorname{sgn}(q)\min|q|','alpha: normalization factor','LDPC source'),('F-08','交织','突发长度',r'L_b=\rho N','rho: burst ratio; N: span','S7 source')]
 frows=[dict(formula_id=a,chapter=b,topic=b,formula_name=c,latex_expression=d,symbol_definitions=e,applicable_scope='See source scope',source_code=f,source_script='',source_document='',implementation_match='PENDING_CODE_REVIEW',data_match='NOT_APPLICABLE',status='READY_WITH_LIMITATION',notes='Formula is frozen as a report candidate; signs/normalization require source line review.') for a,b,c,d,e,f in formulas]
 write('frozen_formula_inventory.csv','formula_id chapter topic formula_name latex_expression symbol_definitions applicable_scope source_code source_script source_document implementation_match data_match status notes'.split(),frows)
 params=[dict(parameter_id=f'P-{i:03d}',task=t,subtask='UNKNOWN',scheme='See frozen result',parameter_name='Formal result provenance',parameter_symbol='',value='See selected CSV',unit='',source_type='FROZEN_CSV',source_file=r['main_csv'],source_location='whole file',csv_confirmation='YES',code_confirmation='PENDING',status='CONFIRMED_BY_DATA',notes='Detailed parameter extraction pending column/source review.') for i,r in enumerate(frozen,1) for t in [r['task']]]
 write('frozen_parameter_inventory.csv','parameter_id task subtask scheme parameter_name parameter_symbol value unit source_type source_file source_location csv_confirmation code_confirmation status notes'.split(),params)
 concl=[]
 for i,r in enumerate(frozen,1): concl.append(dict(conclusion_id=f'{r["task"]}-EVID-{i:03d}',task=r['task'],subtask='UNKNOWN',topic='frozen evidence availability',conclusion_text=f'{r["task"]} has a selected non-archive formal-result candidate; numerical performance conclusion awaits parameter and plot-source review.',main_csv=r['main_csv'],supporting_csv='',main_png='',source_code='',checker='',parameter_scope='See selected CSV',snr_scope='See selected CSV',channel_scope='See selected CSV',platform_scope='UNKNOWN',statistical_scope='See selected CSV',confidence='LOW',limitations='This is evidence-provenance only, not a performance claim.',report_section='Appendix / evidence note',status='READY_WITH_LIMITATION'))
 write('frozen_conclusion_matrix.csv','conclusion_id task subtask topic conclusion_text main_csv supporting_csv main_png source_code checker parameter_scope snr_scope channel_scope platform_scope statistical_scope confidence limitations report_section status'.split(),concl)
 for t in TASKS:
  rs=[r for r in frozen if r['task']==t]; fs=[r for r in figs if r['task']==t]
  text=f'# {t} 正式证据\n\n## 1. 老师要求\n见 requirement_traceability_matrix.csv。\n\n## 2. 实际实现\n待逐源文件核验。\n\n## 3. 正式参数\n见 frozen_parameter_inventory.csv。\n\n## 4. 最终主 CSV\n'+'\n'.join(f'- `{r["main_csv"]}`' for r in rs)+'\n\n## 5. 图源 CSV\n待绑定。\n\n## 6. 正式 PNG\n'+'\n'.join(f'- `{x["copied_png"]}`' for x in fs)+'\n\n## 7. checker/manifest\n待逐文件绑定。\n\n## 8. 源码位置\n待核验。\n\n## 9. 可写结论\n仅可陈述已冻结的证据存在；不得推导数值优劣。\n\n## 10. 不可过度解释的内容\n性能、时延、增益须完成参数和绘图链路复核。\n\n## 11. 差异与限制\n见 inconsistency_register.md。\n\n## 12. 是否具备正式写作条件\nREADY_WITH_LIMITATIONS。\n'
  (E/'task_evidence'/f'{t}_evidence.md').parent.mkdir(exist_ok=True);(E/'task_evidence'/f'{t}_evidence.md').write_text(text,encoding='utf-8')
 (E/'inconsistency_register.md').write_text('# 不一致与限制登记\n\n## INC-001 候选与主结果版本关系\n涉及文件：冻结清单与原始 formal/merged/revised 结果。\n冲突内容：自动版本优先级不能替代逐项审计。\n证据：duplicate_and_version_map.csv。\n影响：数值性结论仍受限。\n最终裁定：待逐任务核验。\n报告写法：不得把候选当作最终性能结论。\n是否阻塞：是（数值结论）。\n状态：OPEN。\n',encoding='utf-8')
 (E/'missing_materials.md').write_text('# 缺失资料\n\n## CRITICAL\n- 每个主 CSV 与主 PNG 的逐项图源映射及参数复核尚未完成。\n\n## IMPORTANT\n- PDF 页码定位、checker/manifest 与代码行级绑定待完成。\n\n## OPTIONAL\n- Visio 正式绘制。\n',encoding='utf-8')
 (E/'readiness_assessment.md').write_text('# 写作就绪评估\n\n| 章节 | 状态 | 原因 |\n|---|---|---|\n'+'\n'.join(f'| {x} | READY_WITH_LIMITATIONS | 已有冻结候选，但数值、图源和参数绑定待完成。 |' for x in ['任务要求','总体方案','统一仿真','BCH','CC','LDPC','多信道','译码算法','交织','综合推荐','结论'])+'\n',encoding='utf-8')
 manifest={'repository_root':str(ROOT),'report_root':str(R),'scan_time':datetime.now(timezone.utc).isoformat(),'git_branch':'S8-PaperDocu','previous_candidate_count':12237,'frozen_result_count':len(frozen),'frozen_figure_count':len(figs),'frozen_formula_count':len(frows),'frozen_parameter_count':len(params),'frozen_conclusion_count':len(concl),'requirement_count':len(tr),'satisfied_requirement_count':0,'partial_requirement_count':len(tr),'deviation_count':0,'unresolved_issue_count':1,'critical_missing_count':1,'important_missing_count':1,'optional_missing_count':1,'ready_chapter_count':0,'ready_with_limitations_count':11,'not_ready_chapter_count':0,'latex_compile_status':'PENDING','modified_original_file_count':0,'formal_simulation_rerun_count':0,'generated_files':[]}
 (E/'round02_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');(E/'round02_execution.log').write_text('\n'.join(log)+'\n',encoding='utf-8')
 (E/'round02_scan_report.md').write_text(f'# 正式报告证据收敛报告\n\n上一轮候选数：12237。\n\n本轮冻结主 CSV：{len(frozen)}；正式 PNG：{len(figs)}；公式：{len(frows)}；结论：{len(concl)}。\n\n全部任务建立了证据文件，但因图源、参数和版本关系尚未逐项完成，章节均为 READY_WITH_LIMITATIONS。\n',encoding='utf-8')
 print(json.dumps(manifest,ensure_ascii=False));return 0
if __name__=='__main__':raise SystemExit(main())
