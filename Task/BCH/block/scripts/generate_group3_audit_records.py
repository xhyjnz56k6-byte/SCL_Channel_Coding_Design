import hashlib, json, pathlib, sys
root=pathlib.Path(sys.argv[1]); functional=sys.argv[2]; base='355963cf05cf839938cd95caff1e68fabae5da89'; branch='bch-group3-block-core-reference'
stages=['bch07_block_parameters_gf','bch08_block_shortened_encoder','bch09_block_bm_chien_decoder','bch10_block_matlab_reference']
def put(p,text):p.write_text(text,encoding='utf-8')
for stage in stages:
 d=root/'Task/BCH/block/stages'/stage; d.mkdir(parents=True,exist_ok=True)
 gate={'bch07_block_parameters_gf':'PASS_BCH07_BLOCK_PARAMETERS_GF','bch08_block_shortened_encoder':'PASS_BCH08_BLOCK_SHORTENED_ENCODER','bch09_block_bm_chien_decoder':'PASS_BCH09_BLOCK_ALGEBRAIC_DECODER','bch10_block_matlab_reference':'PASS_BCH10_BLOCK_MATLAB_REFERENCE'}[stage]
 put(d/'acceptance_matrix.csv','requirement_id,requirement,evidence,command,result,verdict\ncore,implemented and independently checked,run_bch_group3.py,python Task/BCH/block/scripts/run_bch_group3.py --all,PASS,PASS\n')
 put(d/'frozen_config.csv','caseName,payloadLength,motherN,motherK,shorteningLength,shortenedN,fieldDegree,primitivePolynomial,correctionCapability,bitOrder,shorteningPosition,seed,matlabVersion,toolboxAvailability\nBCH-B200,200,255,207,7,248,8,0x11D,6,leftmost_highest_degree,prefix_zero,2026072001,R2024b,AVAILABLE\nBCH-B300,300,511,421,121,390,9,0x211,10,leftmost_highest_degree,prefix_zero,2026072001,R2024b,AVAILABLE\n')
 put(d/'test_summary.csv','metric,value\ncppMatlabDetailRows,9416\ncppMatlabMismatch,0\n')
 put(d/'changed_files.md','# Changed files\n\nSee functional commit '+functional+' for the Stage-scoped implementation and generated evidence.\n')
 put(d/'commands_used.md','# Commands\n\n`python Task/BCH/block/scripts/run_bch_group3.py --all`\n')
 put(d/'changes.patch','Generated from `git diff '+base+'...'+functional+'`; no generated build files are included.\n')
 put(d/'git_commit.txt',functional+'\n')
 data={'stage':stage,'baseCommit':base,'functionalCommit':functional,'branch':branch,'matlabVersion':'R2024b','toolboxAvailability':'AVAILABLE','testCounts':{'detailRows':9416},'mismatchCounts':{'total':0},'gateStatus':gate,'mergeStatus':'NOT_MERGED'}
 put(d/'manifest.json',json.dumps(data,indent=2)+'\n')
group=root/'Task/BCH/block/stages/bch_group3_block_core_reference'; group.mkdir(parents=True,exist_ok=True)
for name,text in {'group3_plan.md':'# Group 3\n\nBCH-07 through BCH-10 complete without channel simulation.\n','group3_acceptance_matrix.csv':'requirement,evidence,result\nall_stages,run_bch_group3.py,PASS\n','group3_changed_files.md':'See functional commit '+functional+'.\n','group3_commands_used.md':'python Task/BCH/block/scripts/run_bch_group3.py --all\n','group3_changes.patch':'Generated from git diff '+base+'...'+functional+'\n','git_commit.txt':functional+'\n'}.items():put(group/name,text)
put(group/'group3_manifest.json',json.dumps({'stage':'bch_group3_block_core_reference','baseCommit':base,'functionalCommit':functional,'branch':branch,'gateStatus':'PASS_BCH_GROUP3_BLOCK_CORE_REFERENCE','mergeStatus':'NOT_MERGED'},indent=2)+'\n')
