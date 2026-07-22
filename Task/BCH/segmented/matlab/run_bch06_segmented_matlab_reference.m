function run_bch06_segmented_matlab_reference(configPath, outputDirectory)
% Independent BCH-06 reference: MATLAB never consumes C++ outputs as truth.
if nargin < 2, error('BCH06:Usage','configPath and outputDirectory are required.'); end
if ~exist(outputDirectory,'dir'), mkdir(outputDirectory); end
config = validate_config_path(configPath);
table = bch15_build_lookup_reference();
write_environment(outputDirectory, config);
write_single_block_reference(outputDirectory, table);
write_frame_pool_audit(outputDirectory);
write_segmented_noiseless_detail(outputDirectory, table);
write_segmented_single_error_detail(outputDirectory, table);
write_multi_block_single_error_detail(outputDirectory, table);
write_same_block_double_error_detail(outputDirectory, table);
write_filler_boundary_detail(outputDirectory, table);
write_failure_status_retention_detail(outputDirectory, table);
write_fixed_multi_error_detail(outputDirectory, table);
invalid = write_invalid_input_audit(outputDirectory, table);
write_summary(outputDirectory, table, invalid, config);
end

function write_single_block_reference(outputDirectory, table)
fenc=checked_open(fullfile(outputDirectory,'matlab_encoder_reference.csv'));
fsyn=checked_open(fullfile(outputDirectory,'matlab_syndrome_reference.csv'));
fno=checked_open(fullfile(outputDirectory,'matlab_no_error_decode.csv'));
fone=checked_open(fullfile(outputDirectory,'matlab_single_error_decode.csv'));
fprintf(fenc,'messageIndex,messageBits,parityBits,codewordBits,syndromeBits,syndromeValue\n');
fprintf(fsyn,'errorPosition,syndromeBits,syndromeValue\n');
fprintf(fno,'messageIndex,messageBits,receivedBits,syndromeBefore,syndromeAfter,lookupHit,correctedPosition,status,correctedCodeword,decodedMessage\n');
fprintf(fone,'messageIndex,errorPosition,receivedBits,syndromeBefore,syndromeAfter,lookupHit,correctedPosition,status,correctedCodeword,decodedMessage\n');
for p=0:14
    fprintf(fsyn,'%d,%s,%d\n',p,bch15_bits_to_string(table(p+1).syndromeBits),table(p+1).syndrome);
end
for index=0:2047
    message=bch15_message_from_decimal(index); codeword=bch15_encode_reference(message); syndrome=bch15_syndrome_reference(codeword);
    fprintf(fenc,'%d,%s,%s,%s,%s,%d\n',index,bch15_bits_to_string(message),bch15_bits_to_string(codeword(12:15)),bch15_bits_to_string(codeword),bch15_bits_to_string(syndrome),bch15_syndrome_value(syndrome));
    d=bch15_lookup_decode_reference(codeword,table);
    fprintf(fno,'%d,%s,%s,%s,%s,%s,%d,%s,%s,%s\n',index,bch15_bits_to_string(message),bch15_bits_to_string(codeword),bch15_bits_to_string(d.syndromeBefore),bch15_bits_to_string(d.syndromeAfter),tf(d.lookupHit),d.correctedPosition,d.status,bch15_bits_to_string(d.correctedCodeword),bch15_bits_to_string(d.decodedMessage));
    for p=0:14
        received=codeword; received(p+1)=xor(received(p+1),1); d=bch15_lookup_decode_reference(received,table);
        fprintf(fone,'%d,%d,%s,%s,%s,%s,%d,%s,%s,%s\n',index,p,bch15_bits_to_string(received),bch15_bits_to_string(d.syndromeBefore),bch15_bits_to_string(d.syndromeAfter),tf(d.lookupHit),d.correctedPosition,d.status,bch15_bits_to_string(d.correctedCodeword),bch15_bits_to_string(d.decodedMessage));
    end
end
checked_close(fenc); checked_close(fsyn); checked_close(fno); checked_close(fone);
end

function write_frame_pool_audit(outputDirectory)
fid=checked_open(fullfile(outputDirectory,'matlab_frame_pool_audit.csv'));
fprintf(fid,'caseName,poolId,frameIndex,payloadLength,payloadBits,pass\n');
for caseName={'BCH-S200','BCH-S300'}
    cfg=bch15_segmented_config_reference(caseName{1}); [values,poolId]=pool_payloads(cfg);
    for index=0:99
        fprintf(fid,'%s,%s,%d,%d,%s,true\n',caseName{1},poolId,index,cfg.payloadLength,bch15_bits_to_string(values{index+1}));
    end
end
checked_close(fid);
end

function write_segmented_noiseless_detail(outputDirectory, table)
fid=checked_open(fullfile(outputDirectory,'matlab_segmented_noiseless_detail.csv'));
fprintf(fid,'caseName,sourceKind,sourceName,frameIndex,poolId,payloadLength,payloadBits,paddedMessageBits,encodedLength,encodedBits,recoveredPaddedMessage,recoveredPayload,blockStatusSequence,noErrorBlocks,correctedBlocks,lookupHitBlocks,lookupMissBlocks,postCheckFailedBlocks,unrecognizedSyndromeBlocks,paddedInformationWrongBlocks,originalPayloadWrongBlocks,fillerOnlyInformationMismatchBlocks,payloadRecovered,pass\n');
for caseName={'BCH-S200','BCH-S300'}
    cfg=bch15_segmented_config_reference(caseName{1});
    for mode=0:3
        payload=synthetic_payload(cfg.payloadLength,mode);
        write_segmented_row(fid,caseName{1},'synthetic',num2str(mode),-1,'',payload,table);
    end
    [values,poolId]=pool_payloads(cfg);
    for index=0:99
        write_segmented_row(fid,caseName{1},'pool','pool',index,poolId,values{index+1},table);
    end
end
checked_close(fid);
end

function write_segmented_row(fid,caseName,kind,name,index,poolId,payload,table)
cfg=bch15_segmented_config_reference(caseName);
e=bch15_segmented_encode_reference(caseName,payload);
d=bch15_segmented_decode_reference(caseName,e.encodedBits,table);
stats=frame_stats(payload,d);
pass=isequal(d.recoveredPayload,payload)&&d.frameDetail.noErrorBlocks==cfg.blockCount&&stats.paddedInformationWrongBlocks==0&&stats.originalPayloadWrongBlocks==0;
fprintf(fid,'%s,%s,%s,%d,%s,%d,%s,%s,%d,%s,%s,%s,%s,%d,%d,%d,%d,%d,%d,%d,%d,%d,%s,%s\n',caseName,kind,name,index,poolId,numel(payload),bch15_bits_to_string(payload),bch15_bits_to_string(e.paddedMessageBits),numel(e.encodedBits),bch15_bits_to_string(e.encodedBits),bch15_bits_to_string(d.recoveredPaddedMessage),bch15_bits_to_string(d.recoveredPayload),status_sequence(d),d.frameDetail.noErrorBlocks,d.frameDetail.correctedBlocks,d.frameDetail.lookupHitBlocks,d.frameDetail.lookupMissBlocks,d.frameDetail.postCheckFailedBlocks,d.frameDetail.unrecognizedSyndromeBlocks,stats.paddedInformationWrongBlocks,stats.originalPayloadWrongBlocks,stats.fillerOnlyInformationMismatchBlocks,tf(isequal(d.recoveredPayload,payload)),tf(pass));
end

function write_segmented_single_error_detail(outputDirectory,table)
fid=checked_open(fullfile(outputDirectory,'matlab_segmented_single_error_detail.csv'));
fprintf(fid,'caseName,blockIndex,localPosition,globalPosition,payloadBits,originalEncodedBits,receivedBits,status,lookupHit,correctedPosition,correctedCodeword,decodedBlockMessage,recoveredPayload,correctedBlocks,paddedInformationWrongBlocks,originalPayloadWrongBlocks,fillerOnlyInformationMismatchBlocks,payloadRecovered,pass\n');
for caseName={'BCH-S200','BCH-S300'}
 cfg=bch15_segmented_config_reference(caseName{1}); p=synthetic_payload(cfg.payloadLength,2); e=bch15_segmented_encode_reference(caseName{1},p);
 for b=0:cfg.blockCount-1
  for q=0:14
   r=e.encodedBits; g=15*b+q+1; r(g)=xor(r(g),1); d=bch15_segmented_decode_reference(caseName{1},r,table); x=d.blockDetails{b+1}; stats=frame_stats(p,d); original=e.encodedBits(15*b+1:15*b+15);
   pass=isequal(d.recoveredPayload,p)&&strcmp(x.status,'CORRECTED_SINGLE_ERROR')&&x.correctedPosition==q&&isequal(x.correctedCodeword,original)&&d.frameDetail.correctedBlocks==1&&stats.paddedInformationWrongBlocks==0&&stats.originalPayloadWrongBlocks==0;
   fprintf(fid,'%s,%d,%d,%d,%s,%s,%s,%s,%s,%d,%s,%s,%s,%d,%d,%d,%d,%s,%s\n',caseName{1},b,q,g-1,bch15_bits_to_string(p),bch15_bits_to_string(e.encodedBits),bch15_bits_to_string(r),x.status,tf(x.lookupHit),x.correctedPosition,bch15_bits_to_string(x.correctedCodeword),bch15_bits_to_string(x.decodedMessage),bch15_bits_to_string(d.recoveredPayload),d.frameDetail.correctedBlocks,stats.paddedInformationWrongBlocks,stats.originalPayloadWrongBlocks,stats.fillerOnlyInformationMismatchBlocks,tf(isequal(d.recoveredPayload,p)),tf(pass));
  end
 end
end
checked_close(fid);
end

function write_multi_block_single_error_detail(outputDirectory,table)
fid=checked_open(fullfile(outputDirectory,'matlab_multi_block_single_error_detail.csv'));
fprintf(fid,'caseName,scenarioName,errorPositions,errorCount,correctedBlocks,blockStatusSequence,paddedInformationWrongBlocks,originalPayloadWrongBlocks,recoveredPayload,payloadRecovered,pass\n');
for caseName={'BCH-S200','BCH-S300'}
 cfg=bch15_segmented_config_reference(caseName{1}); p=synthetic_payload(cfg.payloadLength,3); e=bch15_segmented_encode_reference(caseName{1},p); [names,sets]=multi_block_sets(cfg);
 for z=1:numel(names)
  r=e.encodedBits; globals=zeros(1,size(sets{z},1));
  for j=1:size(sets{z},1), globals(j)=15*sets{z}(j,1)+sets{z}(j,2); r(globals(j)+1)=xor(r(globals(j)+1),1); end
  d=bch15_segmented_decode_reference(caseName{1},r,table); stats=frame_stats(p,d); pass=isequal(d.recoveredPayload,p)&&d.frameDetail.correctedBlocks==size(sets{z},1)&&stats.paddedInformationWrongBlocks==0&&stats.originalPayloadWrongBlocks==0;
  fprintf(fid,'%s,%s,%s,%d,%d,%s,%d,%d,%s,%s,%s\n',caseName{1},names{z},join_positions(globals),numel(globals),d.frameDetail.correctedBlocks,status_sequence(d),stats.paddedInformationWrongBlocks,stats.originalPayloadWrongBlocks,bch15_bits_to_string(d.recoveredPayload),tf(isequal(d.recoveredPayload,p)),tf(pass));
 end
end
checked_close(fid);
end

function write_same_block_double_error_detail(outputDirectory,table)
fid=checked_open(fullfile(outputDirectory,'matlab_same_block_double_error_detail.csv'));
fprintf(fid,'caseName,scenarioName,blockIndex,localPositions,payloadBits,originalCodeword,receivedCodeword,status,lookupHit,correctedPosition,correctedCodeword,decodedBlockMessage,codewordRecovered,payloadRecovered,blockInformationWrong,originalPayloadWrong,fillerOnlyInformationMismatch,reportedSuccessWrongBlockInformation,reportedSuccessWrongOriginalPayload,pass\n');
for caseName={'BCH-S200','BCH-S300'}
 cfg=bch15_segmented_config_reference(caseName{1}); p=synthetic_payload(cfg.payloadLength,3); e=bch15_segmented_encode_reference(caseName{1},p); scenarios=same_block_sets(cfg);
 for z=1:numel(scenarios)
  sc=scenarios{z}; r=e.encodedBits; globals=15*sc.block+sc.localPositions; for j=1:numel(globals), r(globals(j)+1)=xor(r(globals(j)+1),1); end
  d=bch15_segmented_decode_reference(caseName{1},r,table); stats=frame_stats(p,d); x=d.blockDetails{sc.block+1}; original=e.encodedBits(15*sc.block+1:15*sc.block+15); received=r(15*sc.block+1:15*sc.block+15);
  blockWrong=stats.paddedInformationWrongBlocks>0; originalWrong=stats.originalPayloadWrongBlocks>0; fillerOnly=stats.fillerOnlyInformationMismatchBlocks>0; pass=blockWrong&&strcmp(x.status,'CORRECTED_SINGLE_ERROR');
  fprintf(fid,'%s,%s,%d,%s,%s,%s,%s,%s,%s,%d,%s,%s,%s,%s,%s,%s,%s,%d,%d,%s\n',caseName{1},sc.name,sc.block,join_positions(sc.localPositions),bch15_bits_to_string(p),bch15_bits_to_string(original),bch15_bits_to_string(received),x.status,tf(x.lookupHit),x.correctedPosition,bch15_bits_to_string(x.correctedCodeword),bch15_bits_to_string(x.decodedMessage),tf(isequal(x.correctedCodeword,original)),tf(isequal(d.recoveredPayload,p)),tf(blockWrong),tf(originalWrong),tf(fillerOnly),stats.reportedSuccessWrongBlockInformation,stats.reportedSuccessWrongOriginalPayload,tf(pass));
 end
end
checked_close(fid);
end

function write_filler_boundary_detail(outputDirectory,table)
fid=checked_open(fullfile(outputDirectory,'matlab_filler_boundary_detail.csv'));
fprintf(fid,'caseName,lastBlockIndex,localPosition,globalPosition,bitClass,status,correctedPosition,payloadRecovered,pass\n');
for caseName={'BCH-S200','BCH-S300'}
 cfg=bch15_segmented_config_reference(caseName{1}); p=synthetic_payload(cfg.payloadLength,3); e=bch15_segmented_encode_reference(caseName{1},p); last=cfg.blockCount-1;
 for local=0:14
  r=e.encodedBits; g=15*last+local; r(g+1)=xor(r(g+1),1); d=bch15_segmented_decode_reference(caseName{1},r,table); x=d.blockDetails{last+1};
  pass=isequal(d.recoveredPayload,p)&&strcmp(x.status,'CORRECTED_SINGLE_ERROR')&&x.correctedPosition==local;
  fprintf(fid,'%s,%d,%d,%d,%s,%s,%d,%s,%s\n',caseName{1},last,local,g,filler_class(cfg,local),x.status,x.correctedPosition,tf(isequal(d.recoveredPayload,p)),tf(pass));
 end
end
checked_close(fid);
end

function write_failure_status_retention_detail(outputDirectory,table)
fid=checked_open(fullfile(outputDirectory,'matlab_failure_status_retention_detail.csv'));
fprintf(fid,'caseName,injectedFailure,reportedStatus,postCheckFailedBlocks,unrecognizedSyndromeBlocks,lookupHitBlocks,lookupMissBlocks,noErrorBlocks,recoveredPaddedMessage,expectedPaddedMessage,recoveredPaddedMessagePreserved,recoveredPayload,pass\n');
for caseName={'BCH-S200','BCH-S300'}
 cfg=bch15_segmented_config_reference(caseName{1}); p=synthetic_payload(cfg.payloadLength,3); e=bch15_segmented_encode_reference(caseName{1},p); r=e.encodedBits; r(1)=xor(r(1),1);
 bad=table; bad(1).errorPosition=15; d=bch15_segmented_decode_reference(caseName{1},r,bad); ok=strcmp(d.blockDetails{1}.status,'POST_CHECK_FAILED')&&d.frameDetail.postCheckFailedBlocks==1;
 fprintf(fid,'%s,POST_CHECK_FAILED,%s,%d,%d,%d,%d,%d,%s,%s,%s,%s,%s\n',caseName{1},d.blockDetails{1}.status,d.frameDetail.postCheckFailedBlocks,d.frameDetail.unrecognizedSyndromeBlocks,d.frameDetail.lookupHitBlocks,d.frameDetail.lookupMissBlocks,d.frameDetail.noErrorBlocks,bch15_bits_to_string(d.recoveredPaddedMessage),bch15_bits_to_string(e.paddedMessageBits),tf(isequal(d.recoveredPaddedMessage,e.paddedMessageBits)),bch15_bits_to_string(d.recoveredPayload),tf(ok));
 bad=table; for j=1:15, bad(j).syndrome=0; end; d=bch15_segmented_decode_reference(caseName{1},r,bad); ok=strcmp(d.blockDetails{1}.status,'UNRECOGNIZED_SYNDROME')&&d.frameDetail.unrecognizedSyndromeBlocks==1&&d.frameDetail.lookupMissBlocks==1;
 fprintf(fid,'%s,UNRECOGNIZED_SYNDROME,%s,%d,%d,%d,%d,%d,%s,%s,%s,%s,%s\n',caseName{1},d.blockDetails{1}.status,d.frameDetail.postCheckFailedBlocks,d.frameDetail.unrecognizedSyndromeBlocks,d.frameDetail.lookupHitBlocks,d.frameDetail.lookupMissBlocks,d.frameDetail.noErrorBlocks,bch15_bits_to_string(d.recoveredPaddedMessage),bch15_bits_to_string(e.paddedMessageBits),tf(isequal(d.recoveredPaddedMessage,e.paddedMessageBits)),bch15_bits_to_string(d.recoveredPayload),tf(ok));
end
checked_close(fid);
end

function write_fixed_multi_error_detail(outputDirectory,table)
fid=checked_open(fullfile(outputDirectory,'matlab_fixed_multi_error_detail.csv'));
fprintf(fid,'seedId,errorWeight,messageIndex,messageBits,originalCodeword,errorPositions,receivedBits,syndromeBefore,lookupHit,correctedPosition,syndromeAfter,status,correctedCodeword,decodedMessage,codewordRecovered,payloadRecovered,miscorrection,pass\n');
seeds=fixed_seeds(); messages={zeros(1,11),ones(1,11),[1 0 1 0 1 0 1 0 1 0 1],[0 1 0 1 0 1 0 1 0 1 0]};
for s=1:numel(seeds)
 for m=1:numel(messages)
  c=bch15_encode_reference(messages{m}); r=c; for j=1:numel(seeds{s}.positions), r(seeds{s}.positions(j)+1)=xor(r(seeds{s}.positions(j)+1),1); end
  d=bch15_lookup_decode_reference(r,table); cw=isequal(d.correctedCodeword,c); payload=isequal(d.decodedMessage,messages{m}); misc=strcmp(d.status,'CORRECTED_SINGLE_ERROR')&&~payload;
  fprintf(fid,'%s,%d,%d,%s,%s,%s,%s,%s,%s,%d,%s,%s,%s,%s,%s,%s,%s,true\n',seeds{s}.id,seeds{s}.weight,m-1,bch15_bits_to_string(messages{m}),bch15_bits_to_string(c),join_positions(seeds{s}.positions),bch15_bits_to_string(r),bch15_bits_to_string(d.syndromeBefore),tf(d.lookupHit),d.correctedPosition,bch15_bits_to_string(d.syndromeAfter),d.status,bch15_bits_to_string(d.correctedCodeword),bch15_bits_to_string(d.decodedMessage),tf(cw),tf(payload),tf(misc));
 end
end
checked_close(fid);
end

function invalid = write_invalid_input_audit(outputDirectory, table)
fid=checked_open(fullfile(outputDirectory,'matlab_invalid_input_audit.csv'));
fprintf(fid,'testId,functionName,expectedErrorId,actualErrorId,expectedMessageKeyword,actualMessage,caught,pass\n');
tests={...
 {'MI_01','bch15_encode_reference','BCH06:InvalidBits','binary',@() bch15_encode_reference(zeros(1,10))};...
 {'MI_02','bch15_encode_reference','BCH06:InvalidBits','binary',@() bch15_encode_reference(zeros(1,12))};...
 {'MI_03','bch15_encode_reference','BCH06:InvalidBits','binary',@() bch15_encode_reference([zeros(1,10) 2])};...
 {'MI_04','bch15_encode_reference','BCH06:InvalidBits','binary',@() bch15_encode_reference([zeros(1,10) -1])};...
 {'MI_05','bch15_encode_reference','BCH06:InvalidBits','row vector',@() bch15_encode_reference(zeros(11,1))};...
 {'RI_01','bch15_lookup_decode_reference','BCH06:InvalidBits','binary',@() bch15_lookup_decode_reference(zeros(1,14),table)};...
 {'RI_02','bch15_lookup_decode_reference','BCH06:InvalidBits','binary',@() bch15_lookup_decode_reference(zeros(1,16),table)};...
 {'RI_03','bch15_lookup_decode_reference','BCH06:InvalidBits','binary',@() bch15_lookup_decode_reference([zeros(1,14) 2],table)};...
 {'RI_04','bch15_lookup_decode_reference','BCH06:InvalidBits','binary',@() bch15_lookup_decode_reference([zeros(1,14) -1],table)};...
 {'RI_05','bch15_lookup_decode_reference','BCH06:InvalidBits','row vector',@() bch15_lookup_decode_reference(zeros(15,1),table)};...
 {'TI_01','bch15_lookup_decode_reference','MATLAB:nonExistentField','syndrome',@() bch15_lookup_decode_reference(error_pattern(),rmfield(table,'syndrome'))};...
 {'TI_02','bch15_lookup_decode_reference','MATLAB:nonExistentField','errorPosition',@() bch15_lookup_decode_reference(error_pattern(),rmfield(table,'errorPosition'))};...
 {'TI_03','local_validate_table','BCH06:InvalidTable','syndrome',@() local_validate_table(setfield(table,{1},'syndrome',1.5))};...
 {'TI_04','local_validate_table','BCH06:InvalidTable','syndrome',@() local_validate_table(setfield(table,{1},'syndrome',-1))};...
 {'TI_05','local_validate_table','BCH06:InvalidTable','syndrome',@() local_validate_table(setfield(table,{1},'syndrome',16))};...
 {'TI_06','local_validate_table','BCH06:InvalidTable','errorPosition',@() local_validate_table(setfield(table,{1},'errorPosition',1.5))};...
 {'TI_07','local_validate_table','BCH06:InvalidTable','errorPosition',@() local_validate_table(setfield(table,{1},'errorPosition','bad'))};...
 {'DI_01','local_divisor_check','BCH06:InvalidDivisor','divisor',@() local_divisor_check([0 1 1])};...
 {'DI_02','local_divisor_check','BCH06:InvalidDivisor','divisor',@() local_divisor_check([0 0 0])};...
 {'BI_01','local_bit_string_check','BCH06:InvalidBitString','0/1',@() local_bit_string_check('01012')};...
};
failed=0;
for i=1:numel(tests)
    t=tests{i}; [caught,id,msg]=expect_error(t{5}); pass=caught&&(strcmp(id,t{3})||contains(msg,t{4}));
    failed=failed+~pass; fprintf(fid,'%s,%s,%s,%s,%s,%s,%s,%s\n',t{1},t{2},t{3},id,t{4},csv_safe(msg),tf(caught),tf(pass));
end
checked_close(fid);
invalid.cases=numel(tests); invalid.failures=failed;
end

function write_summary(outputDirectory,table,invalid,config)
metrics=segmented_metrics(table);
single=single_block_metrics(table);
if metrics.fixedMultiErrorCases~=config.fixedMultiErrorExpectedCount
    error('BCH06:Config','fixed multi-error count does not match configPath');
end
fid=checked_open(fullfile(outputDirectory,'matlab_test_summary.csv'));
fprintf(fid,'metric,value\n');
base={'fixedVectorCases',single.fixedVectorCases;'matlabFixedVectorMismatch',single.matlabFixedVectorMismatch;'encoderCases',single.encoderCases;'matlabEncodedMismatch',single.matlabEncodedMismatch;'matlabParityMismatch',single.matlabParityMismatch;'legalSyndromeCases',single.legalSyndromeCases;'matlabLegalSyndromeMismatch',single.matlabLegalSyndromeMismatch;'singleErrorSyndromeCases',single.singleErrorSyndromeCases;'matlabSingleErrorSyndromeMismatch',single.matlabSingleErrorSyndromeMismatch;'matlabLookupPositionMismatch',single.matlabLookupPositionMismatch;'noErrorDecodeCases',single.noErrorDecodeCases;'matlabNoErrorDecodeMismatch',single.matlabNoErrorDecodeMismatch;'singleErrorDecodeCases',single.singleErrorDecodeCases;'matlabSingleErrorDecodeMismatch',single.matlabSingleErrorDecodeMismatch;'matlabInvalidInputCases',invalid.cases;'matlabInvalidInputFailureCount',invalid.failures;'fixedMultiErrorExpectedCount',config.fixedMultiErrorExpectedCount};
for i=1:size(base,1), fprintf(fid,'%s,%d\n',base{i,1},base{i,2}); end
names=fieldnames(metrics); for i=1:numel(names), fprintf(fid,'%s,%d\n',names{i},metrics.(names{i})); end
checked_close(fid);
end

function m=segmented_metrics(table)
m=struct('segmentedNoiselessFrames',0,'segmentedNoiselessMismatch',0,'segmentedSingleErrorCases',0,'segmentedSingleErrorMismatch',0,'multiBlockSingleErrorCases',0,'multiBlockSingleErrorMismatch',0,'sameBlockDoubleErrorCases',0,'doubleErrorClassificationMismatch',0,'reportedSuccessWrongBlockInformation',0,'reportedSuccessWrongOriginalPayload',0,'fillerOnlyInformationMismatch',0,'fillerBoundaryCases',0,'fillerBoundaryMismatch',0,'failureStatusRetentionCases',0,'failureStatusRetentionMismatch',0,'fixedMultiErrorCases',0,'fixedMultiErrorMismatch',0);
for caseName={'BCH-S200','BCH-S300'}
    cfg=bch15_segmented_config_reference(caseName{1}); payloads=[{synthetic_payload(cfg.payloadLength,0),synthetic_payload(cfg.payloadLength,1),synthetic_payload(cfg.payloadLength,2),synthetic_payload(cfg.payloadLength,3)}, pool_payloads(cfg)];
    for i=1:numel(payloads), e=bch15_segmented_encode_reference(caseName{1},payloads{i}); d=bch15_segmented_decode_reference(caseName{1},e.encodedBits,table); s=frame_stats(payloads{i},d); m.segmentedNoiselessFrames=m.segmentedNoiselessFrames+1; m.segmentedNoiselessMismatch=m.segmentedNoiselessMismatch+~(isequal(d.recoveredPayload,payloads{i})&&s.paddedInformationWrongBlocks==0); end
    p=synthetic_payload(cfg.payloadLength,2); e=bch15_segmented_encode_reference(caseName{1},p);
    for b=0:cfg.blockCount-1, for q=0:14, r=e.encodedBits; r(15*b+q+1)=xor(r(15*b+q+1),1); d=bch15_segmented_decode_reference(caseName{1},r,table); s=frame_stats(p,d); ok=isequal(d.recoveredPayload,p)&&strcmp(d.blockDetails{b+1}.status,'CORRECTED_SINGLE_ERROR')&&d.blockDetails{b+1}.correctedPosition==q&&s.paddedInformationWrongBlocks==0; m.segmentedSingleErrorCases=m.segmentedSingleErrorCases+1; m.segmentedSingleErrorMismatch=m.segmentedSingleErrorMismatch+~ok; end,end
    p=synthetic_payload(cfg.payloadLength,3); e=bch15_segmented_encode_reference(caseName{1},p); [~,sets]=multi_block_sets(cfg);
    for z=1:numel(sets), r=e.encodedBits; for j=1:size(sets{z},1), r(15*sets{z}(j,1)+sets{z}(j,2)+1)=xor(r(15*sets{z}(j,1)+sets{z}(j,2)+1),1); end; d=bch15_segmented_decode_reference(caseName{1},r,table); ok=isequal(d.recoveredPayload,p); m.multiBlockSingleErrorCases=m.multiBlockSingleErrorCases+1; m.multiBlockSingleErrorMismatch=m.multiBlockSingleErrorMismatch+~ok; end
    scenarios=same_block_sets(cfg);
    for z=1:numel(scenarios), sc=scenarios{z}; r=e.encodedBits; for j=1:numel(sc.localPositions), r(15*sc.block+sc.localPositions(j)+1)=xor(r(15*sc.block+sc.localPositions(j)+1),1); end; d=bch15_segmented_decode_reference(caseName{1},r,table); s=frame_stats(p,d); m.sameBlockDoubleErrorCases=m.sameBlockDoubleErrorCases+1; m.reportedSuccessWrongBlockInformation=m.reportedSuccessWrongBlockInformation+s.reportedSuccessWrongBlockInformation; m.reportedSuccessWrongOriginalPayload=m.reportedSuccessWrongOriginalPayload+s.reportedSuccessWrongOriginalPayload; m.fillerOnlyInformationMismatch=m.fillerOnlyInformationMismatch+s.fillerOnlyInformationMismatchBlocks; end
    last=cfg.blockCount-1; for q=0:14, r=e.encodedBits; r(15*last+q+1)=xor(r(15*last+q+1),1); d=bch15_segmented_decode_reference(caseName{1},r,table); ok=isequal(d.recoveredPayload,p); m.fillerBoundaryCases=m.fillerBoundaryCases+1; m.fillerBoundaryMismatch=m.fillerBoundaryMismatch+~ok; end
    r=e.encodedBits; r(1)=xor(r(1),1); bad=table; bad(1).errorPosition=15; d=bch15_segmented_decode_reference(caseName{1},r,bad); m.failureStatusRetentionCases=m.failureStatusRetentionCases+1; m.failureStatusRetentionMismatch=m.failureStatusRetentionMismatch+~(strcmp(d.blockDetails{1}.status,'POST_CHECK_FAILED')&&d.frameDetail.postCheckFailedBlocks==1);
    bad=table; for j=1:15,bad(j).syndrome=0;end; d=bch15_segmented_decode_reference(caseName{1},r,bad); m.failureStatusRetentionCases=m.failureStatusRetentionCases+1; m.failureStatusRetentionMismatch=m.failureStatusRetentionMismatch+~(strcmp(d.blockDetails{1}.status,'UNRECOGNIZED_SYNDROME')&&d.frameDetail.unrecognizedSyndromeBlocks==1&&d.frameDetail.lookupMissBlocks==1);
end
m.doubleErrorClassificationMismatch=(m.reportedSuccessWrongBlockInformation~=12)||(m.reportedSuccessWrongOriginalPayload~=9)||(m.fillerOnlyInformationMismatch~=3);
fixed=fixed_multi_metrics(table); m.fixedMultiErrorCases=fixed.cases; m.fixedMultiErrorMismatch=fixed.mismatches;
end

function m=single_block_metrics(table)
m=struct('fixedVectorCases',0,'matlabFixedVectorMismatch',0,'encoderCases',0,'matlabEncodedMismatch',0,'matlabParityMismatch',0,'legalSyndromeCases',0,'matlabLegalSyndromeMismatch',0,'singleErrorSyndromeCases',0,'matlabSingleErrorSyndromeMismatch',0,'matlabLookupPositionMismatch',0,'noErrorDecodeCases',0,'matlabNoErrorDecodeMismatch',0,'singleErrorDecodeCases',0,'matlabSingleErrorDecodeMismatch',0);
fixedMessages={'00000000000','10000000000','00000000001','11111111111','10101010101','01010101010'};
fixedCodewords={'000000000000000','100000000001001','000000000010011','111111111111111','101010101011011','010101010100100'};
for i=1:numel(fixedMessages)
    message=binary_vector(fixedMessages{i}); codeword=bch15_encode_reference(message);
    m.fixedVectorCases=m.fixedVectorCases+1;
    m.matlabFixedVectorMismatch=m.matlabFixedVectorMismatch+~isequal(codeword,binary_vector(fixedCodewords{i}));
end
for index=0:2047
    message=bch15_message_from_decimal(index); codeword=bch15_encode_reference(message); syndrome=bch15_syndrome_reference(codeword);
    m.encoderCases=m.encoderCases+1;
    m.matlabEncodedMismatch=m.matlabEncodedMismatch+~(numel(codeword)==15&&isequal(codeword(1:11),message));
    [~,remainder]=bch15_gf2_divide_reference([message zeros(1,4)],[1 0 0 1 1]);
    m.matlabParityMismatch=m.matlabParityMismatch+~isequal(codeword(12:15),remainder);
    m.legalSyndromeCases=m.legalSyndromeCases+1; m.matlabLegalSyndromeMismatch=m.matlabLegalSyndromeMismatch+~isequal(syndrome,zeros(1,4));
    d=bch15_lookup_decode_reference(codeword,table); m.noErrorDecodeCases=m.noErrorDecodeCases+1; m.matlabNoErrorDecodeMismatch=m.matlabNoErrorDecodeMismatch+~(strcmp(d.status,'NO_ERROR')&&isequal(d.decodedMessage,message));
    for position=0:14
        errorBits=zeros(1,15); errorBits(position+1)=1; singleSyndrome=bch15_syndrome_reference(errorBits); d=bch15_lookup_decode_reference(xor(codeword,errorBits),table);
        m.singleErrorSyndromeCases=m.singleErrorSyndromeCases+1;
        m.matlabSingleErrorSyndromeMismatch=m.matlabSingleErrorSyndromeMismatch+~any(singleSyndrome);
        m.matlabLookupPositionMismatch=m.matlabLookupPositionMismatch+~(d.lookupHit&&d.correctedPosition==position);
        m.singleErrorDecodeCases=m.singleErrorDecodeCases+1; m.matlabSingleErrorDecodeMismatch=m.matlabSingleErrorDecodeMismatch+~(strcmp(d.status,'CORRECTED_SINGLE_ERROR')&&isequal(d.decodedMessage,message));
    end
end
end

function m=fixed_multi_metrics(table)
m=struct('cases',0,'mismatches',0); seeds=fixed_seeds(); messages={zeros(1,11),ones(1,11),[1 0 1 0 1 0 1 0 1 0 1],[0 1 0 1 0 1 0 1 0 1 0]};
for s=1:numel(seeds)
    for i=1:numel(messages)
        codeword=bch15_encode_reference(messages{i}); received=codeword;
        for j=1:numel(seeds{s}.positions), received(seeds{s}.positions(j)+1)=xor(received(seeds{s}.positions(j)+1),1); end
        decoded=bch15_lookup_decode_reference(received,table); m.cases=m.cases+1;
        m.mismatches=m.mismatches+~(numel(decoded.correctedCodeword)==15&&numel(decoded.decodedMessage)==11&&isequal(decoded.syndromeAfter,zeros(1,4)));
    end
end
end

function stats=frame_stats(payload,result)
cfg=result.config; padded=[payload zeros(1,cfg.fillerBits)];
stats=struct('paddedInformationWrongBlocks',0,'originalPayloadWrongBlocks',0,'fillerOnlyInformationMismatchBlocks',0,'reportedSuccessWrongBlockInformation',0,'reportedSuccessWrongOriginalPayload',0);
for b=0:cfg.blockCount-1
    expected=padded(11*b+1:11*b+11); decoded=result.blockDetails{b+1}.decodedMessage; paddedOk=isequal(decoded,expected);
    payloadBitsInBlock=11; if b+1==cfg.blockCount, payloadBitsInBlock=11-cfg.fillerBits; end
    originalOk=isequal(decoded(1:payloadBitsInBlock),expected(1:payloadBitsInBlock));
    success=strcmp(result.blockDetails{b+1}.status,'NO_ERROR')||strcmp(result.blockDetails{b+1}.status,'CORRECTED_SINGLE_ERROR');
    if ~paddedOk, stats.paddedInformationWrongBlocks=stats.paddedInformationWrongBlocks+1; if success, stats.reportedSuccessWrongBlockInformation=stats.reportedSuccessWrongBlockInformation+1; end, end
    if ~originalOk, stats.originalPayloadWrongBlocks=stats.originalPayloadWrongBlocks+1; if success, stats.reportedSuccessWrongOriginalPayload=stats.reportedSuccessWrongOriginalPayload+1; end
    elseif ~paddedOk, stats.fillerOnlyInformationMismatchBlocks=stats.fillerOnlyInformationMismatchBlocks+1; end
end
end

function [payloads,poolId]=pool_payloads(cfg)
root=fileparts(fileparts(fileparts(fileparts(fileparts(mfilename('fullpath'))))));
kind=ternary(cfg.payloadLength==200,'k200','k300');
manifestPath=fullfile(root,'Task','Common','build','stage04','real_pool_runs','smoke','frames',kind,'manifest.json');
manifest=jsondecode(fileread(manifestPath));
poolId=manifest.framePoolId; expected=ternary(cfg.payloadLength==200,'payload_k200_seed2026072001_policy1_frames100','payload_k300_seed2026072001_policy1_frames100');
if ~strcmp(poolId,expected)||manifest.payloadLength~=cfg.payloadLength||manifest.totalFrames<100||~strcmp(manifest.bitOrderWithinByte,'lsb_first'), error('BCH06:FramePoolManifest','invalid Common frame pool manifest'); end
payloads=cell(1,100); bytesPerFrame=manifest.bytesPerFrame; written=0; folder=fileparts(manifestPath);
for s=1:numel(manifest.shards)
    shard=manifest.shards(s); start=shard.startFrame; if shard.frameCount<=0, error('BCH06:FramePoolManifest','empty shard'); end
    raw=read_bytes(fullfile(folder,shard.fileName)); if numel(raw)~=shard.sizeBytes, error('BCH06:FramePoolManifest','shard size mismatch'); end
    for local=0:shard.frameCount-1
        frameIndex=start+local; if frameIndex>=100, continue; end
        offset=local*bytesPerFrame; packed=raw(offset+1:offset+bytesPerFrame); expanded=zeros(1,bytesPerFrame*8);
        for i=1:numel(packed), for bit=0:7, expanded((i-1)*8+bit+1)=bitget(packed(i),bit+1); end, end
        payloads{frameIndex+1}=expanded(1:cfg.payloadLength); written=written+1;
    end
end
if written~=100, error('BCH06:FramePoolManifest','missing frame indices'); end
end

function bytes=read_bytes(path)
fid=fopen(path,'rb'); if fid<0, error('BCH06:FramePoolManifest','cannot open shard'); end
bytes=fread(fid,Inf,'*uint8')'; fclose(fid);
end

function [names,sets]=multi_block_sets(cfg)
names={'first_last','adjacent','three_spread','every_block_one'};
sets={ [0 0;cfg.blockCount-1 14], [1 3;2 9], [0 1;floor(cfg.blockCount/2) 7;cfg.blockCount-1 13], [(0:cfg.blockCount-1)' mod((0:cfg.blockCount-1)',15)]};
end

function scenarios=same_block_sets(cfg)
last=cfg.blockCount-1; firstFiller=11-cfg.fillerBits;
scenarios={struct('name','two_payload','block',0,'localPositions',[0 1]),struct('name','payload_parity','block',0,'localPositions',[0 11]),struct('name','two_parity','block',0,'localPositions',[11 12]),struct('name','payload_filler','block',last,'localPositions',[0 firstFiller]),struct('name','two_filler','block',last,'localPositions',[firstFiller firstFiller+1]),struct('name','filler_parity','block',last,'localPositions',[firstFiller 11])};
end

function seeds=fixed_seeds()
base={struct('id','D_01','weight',2,'positions',[0 1]),struct('id','D_02','weight',2,'positions',[0 10]),struct('id','D_03','weight',2,'positions',[0 14]),struct('id','D_04','weight',2,'positions',[1 11]),struct('id','D_05','weight',2,'positions',[2 8]),struct('id','D_06','weight',2,'positions',[4 5]),struct('id','D_07','weight',2,'positions',[10 11]),struct('id','D_08','weight',2,'positions',[11 12]),struct('id','D_09','weight',2,'positions',[12 14]),struct('id','D_10','weight',2,'positions',[3 13]),struct('id','D_11','weight',2,'positions',[6 9]),struct('id','D_12','weight',2,'positions',[7 14])};
root=fileparts(fileparts(fileparts(fileparts(fileparts(mfilename('fullpath'))))));
path=fullfile(root,'Task','BCH','segmented','config','bch15_multi_error_seeds.csv');
fid=fopen(path,'r'); if fid<0, error('BCH06:Seeds','cannot open seed CSV'); end; fgetl(fid); seeds=base;
while true
 line=fgetl(fid); if ~ischar(line), break; end
 parts=regexp(line,',(?=(?:[^"]*"[^"]*")*[^"]*$)','split'); pos=strrep(parts{3},'"',''); vals=str2double(strsplit(pos,';'));
 seeds{end+1}=struct('id',parts{1},'weight',str2double(parts{2}),'positions',vals); %#ok<AGROW>
end
fclose(fid);
end

function p=synthetic_payload(n,mode)
p=zeros(1,n); if mode==1,p(:)=1;elseif mode==2,p=mod(0:n-1,2);elseif mode==3,p(end)=1;end
end

function text=status_sequence(d)
text=''; for i=1:numel(d.blockDetails), if i>1,text=[text ';'];end, text=[text d.blockDetails{i}.status]; end
end

function text=join_positions(values)
if isempty(values), text=''; return; end
text=num2str(values(1)); for i=2:numel(values), text=[text ';' num2str(values(i))]; end
end

function c=filler_class(cfg,local)
payload=11-cfg.fillerBits; if local<payload,c='payload';elseif local<11,c='filler';else,c='parity';end
end

function [caught,id,msg]=expect_error(fn)
caught=false; id=''; msg='';
try, fn(); catch error, caught=true; id=error.identifier; msg=error.message; end
end

function local_validate_table(table)
for i=1:numel(table)
    if ~isnumeric(table(i).syndrome)||table(i).syndrome<0||table(i).syndrome>15||table(i).syndrome~=floor(table(i).syndrome), error('BCH06:InvalidTable','syndrome must be integer 0..15'); end
    if ~isnumeric(table(i).errorPosition)||table(i).errorPosition<0||table(i).errorPosition>15||table(i).errorPosition~=floor(table(i).errorPosition), error('BCH06:InvalidTable','errorPosition must be integer'); end
end
end

function local_divisor_check(divisor)
if isempty(divisor)||all(divisor==0)||divisor(1)~=1, error('BCH06:InvalidDivisor','divisor must start with one and be nonzero'); end
end

function local_bit_string_check(text)
if any(text~='0' & text~='1'), error('BCH06:InvalidBitString','bit string must contain only 0/1'); end
end

function e=error_pattern()
e=zeros(1,15); e(1)=1;
end

function text=csv_safe(text)
text=strrep(text,',',';'); text=strrep(text,sprintf('\n'),' '); text=strrep(text,sprintf('\r'),' ');
for i=1:numel(text)
    if double(text(i))<32 || double(text(i))>126, text(i)='?'; end
end
end

function write_environment(outputDirectory,config)
v=version; fid=checked_open(fullfile(outputDirectory,'matlab_environment.json'));
fprintf(fid,'{"matlabVersion":"%s","platform":"%s","reference":"independent_gf2_long_division","configValidated":true,"fixedMultiErrorExpectedCount":%d}\n',v,computer,config.fixedMultiErrorExpectedCount); checked_close(fid);
fid=checked_open(fullfile(outputDirectory,'matlab_toolbox_audit.csv'));
fprintf(fid,'matlabVersion,toolboxName,functionName,available,used,bitOrderConversion,result,notes\n');
names={'bchenc','bchdec','bchgenpoly','gf'};
for i=1:numel(names)
    available=exist(names{i},'file')>0; result=ternary(available,'AVAILABLE_NOT_USED','UNAVAILABLE');
    fprintf(fid,'%s,Communications Toolbox,%s,%s,false,none,%s,primary_gate_uses_independent_reference\n',v,names{i},tf(available),result);
end
checked_close(fid);
end

function config=validate_config_path(configPath)
if ~(ischar(configPath)||isstring(configPath)) || ~exist(configPath,'file')
    error('BCH06:Config','configPath must name an existing BCH-06 configuration file');
end
lines=regexp(strtrim(fileread(configPath)),'\r?\n','split');
expected={'key,value';'code,"BCH(15,11,1)"';'generatorPolynomial,10011';'bitOrder,leftmost_highest_degree';'S200,200/19/9/285';'S300,300/28/8/420';'fixedMultiErrorExpectedCount,96'};
if numel(lines)~=numel(expected) || ~all(strcmp(lines(:),expected(:)))
    error('BCH06:Config','configPath contents do not match the frozen BCH-06 configuration');
end
config=struct('fixedMultiErrorExpectedCount',96);
end

function bits=binary_vector(text)
if any(text~='0' & text~='1'), error('BCH06:InvalidBitString','bit string must contain only 0/1'); end
bits=double(text)-double('0');
end

function fid=checked_open(path)
fid=fopen(path,'w'); if fid<0, error('BCH06:Output','cannot open output file'); end
end

function checked_close(fid)
if fclose(fid)~=0, error('BCH06:Output','cannot close output file'); end
end

function text=tf(value)
if value, text='true'; else, text='false'; end
end

function value=ternary(test,a,b)
if test, value=a; else, value=b; end
end
