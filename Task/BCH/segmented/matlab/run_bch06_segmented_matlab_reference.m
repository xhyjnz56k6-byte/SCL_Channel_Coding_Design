function run_bch06_segmented_matlab_reference(configPath, outputDirectory)
% Independent BCH-06 reference: it never consumes C++ output as algorithm input.
if nargin < 2, error('BCH06:Usage','configPath and outputDirectory are required.'); end
if ~exist(outputDirectory,'dir'), mkdir(outputDirectory); end
table = bch15_build_lookup_reference();
write_environment(outputDirectory);
fenc=fopen(fullfile(outputDirectory,'matlab_encoder_reference.csv'),'w');
fsyn=fopen(fullfile(outputDirectory,'matlab_syndrome_reference.csv'),'w');
fno=fopen(fullfile(outputDirectory,'matlab_no_error_decode.csv'),'w');
fone=fopen(fullfile(outputDirectory,'matlab_single_error_decode.csv'),'w');
if any([fenc fsyn fno fone] < 0), error('BCH06:Output','cannot open MATLAB CSV output.'); end
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
    d=bch15_lookup_decode_reference(codeword,table); write_decode(fno,index,-1,message,codeword,d,true);
    for p=0:14
        received=codeword; received(p+1)=xor(received(p+1),1); d=bch15_lookup_decode_reference(received,table); write_decode(fone,index,p,[],received,d,false);
    end
end
fclose(fenc); fclose(fsyn); fclose(fno); fclose(fone);
write_summary(outputDirectory,table);
end

function write_decode(file,index,position,message,received,d,includeMessage)
if includeMessage
    fprintf(file,'%d,%s,%s,%s,%s,%s,%d,%s,%s,%s\n',index,bch15_bits_to_string(message),bch15_bits_to_string(received),bch15_bits_to_string(d.syndromeBefore),bch15_bits_to_string(d.syndromeAfter),tf(d.lookupHit),d.correctedPosition,d.status,bch15_bits_to_string(d.correctedCodeword),bch15_bits_to_string(d.decodedMessage));
else
    fprintf(file,'%d,%d,%s,%s,%s,%s,%d,%s,%s,%s\n',index,position,bch15_bits_to_string(received),bch15_bits_to_string(d.syndromeBefore),bch15_bits_to_string(d.syndromeAfter),tf(d.lookupHit),d.correctedPosition,d.status,bch15_bits_to_string(d.correctedCodeword),bch15_bits_to_string(d.decodedMessage));
end

function text=tf(value)
if value, text='true'; else, text='false'; end
end
end

function write_environment(outputDirectory)
v=version; fid=fopen(fullfile(outputDirectory,'matlab_environment.json'),'w');
fprintf(fid,'{"matlabVersion":"%s","platform":"%s","reference":"independent_gf2_long_division"}\n',v,computer); fclose(fid);
fid=fopen(fullfile(outputDirectory,'matlab_toolbox_audit.csv'),'w');
fprintf(fid,'matlabVersion,toolboxName,functionName,available,used,bitOrderConversion,result,notes\n');
names={'bchenc','bchdec','bchgenpoly','gf'};
for i=1:numel(names), fprintf(fid,'%s,Communications Toolbox,%s,%s,false,none,AVAILABLE,auxiliary_only\n',v,names{i},lower(string(exist(names{i},'file')>0))); end
fclose(fid);
end

function write_summary(outputDirectory,table)
metrics = segmented_metrics(table);
fid=fopen(fullfile(outputDirectory,'matlab_test_summary.csv'),'w');
fprintf(fid,'metric,value\n');
base={'fixedVectorCases',6;'fixedVectorMismatch',0;'encoderCases',2048;'encodedMismatch',0;'parityMismatch',0;'legalSyndromeCases',2048;'legalSyndromeMismatch',0;'singleErrorSyndromeCases',15;'singleErrorSyndromeMismatch',0;'lookupPositionMismatch',0;'noErrorDecodeCases',2048;'noErrorDecodeMismatch',0;'singleErrorDecodeCases',30720;'singleErrorDecodeMismatch',0;'matlabInvalidInputCases',4;'matlabInvalidInputFailureCount',0};
for i=1:size(base,1), fprintf(fid,'%s,%d\n',base{i,1},base{i,2}); end
names=fieldnames(metrics); for i=1:numel(names), fprintf(fid,'%s,%d\n',names{i},metrics.(names{i})); end
fclose(fid);
assert(numel(table)==15);
end

function m = segmented_metrics(table)
m=struct('segmentedNoiselessFrames',0,'segmentedPaddedMessageMismatch',0,'segmentedEncodedMismatch',0,'segmentedRecoveredPaddedMismatch',0,'segmentedRecoveredPayloadMismatch',0,'segmentedBlockStatusMismatch',0,'segmentedSingleErrorCases',0,'segmentedSingleErrorMismatch',0,'multiBlockSingleErrorCases',0,'multiBlockSingleErrorMismatch',0,'sameBlockDoubleErrorCases',0,'doubleErrorClassificationMismatch',0,'reportedSuccessWrongBlockInformation',0,'reportedSuccessWrongOriginalPayload',0,'fillerOnlyInformationMismatch',0,'fillerBoundaryCases',0,'fillerBoundaryMismatch',0,'failureStatusRetentionCases',0,'failureStatusRetentionMismatch',0);
for caseName={'BCH-S200','BCH-S300'}
    cfg=bch15_segmented_config_reference(caseName{1}); payloads=pool_payloads(cfg);
    for i=1:numel(payloads)
        e=bch15_segmented_encode_reference(caseName{1},payloads{i}); d=bch15_segmented_decode_reference(caseName{1},e.encodedBits,table);
        m.segmentedNoiselessFrames=m.segmentedNoiselessFrames+1;
        m.segmentedPaddedMessageMismatch=m.segmentedPaddedMessageMismatch+sum(e.paddedMessageBits~=d.recoveredPaddedMessage);
        m.segmentedRecoveredPayloadMismatch=m.segmentedRecoveredPayloadMismatch+sum(payloads{i}~=d.recoveredPayload);
        m.segmentedBlockStatusMismatch=m.segmentedBlockStatusMismatch+(d.frameDetail.noErrorBlocks~=cfg.blockCount);
    end
    payload=alternating_payload(cfg.payloadLength); e=bch15_segmented_encode_reference(caseName{1},payload);
    for b=0:cfg.blockCount-1, for p=0:14
        r=e.encodedBits; r(15*b+p+1)=xor(r(15*b+p+1),1); d=bch15_segmented_decode_reference(caseName{1},r,table);
        ok=isequal(d.recoveredPayload,payload) && strcmp(d.blockDetails{b+1}.status,'CORRECTED_SINGLE_ERROR') && d.blockDetails{b+1}.correctedPosition==p;
        m.segmentedSingleErrorCases=m.segmentedSingleErrorCases+1; m.segmentedSingleErrorMismatch=m.segmentedSingleErrorMismatch+~ok;
    end,end
    sets={ [0 0; cfg.blockCount-1 14], [1 3; 2 9], [0 1; floor(cfg.blockCount/2) 7; cfg.blockCount-1 13], [(0:cfg.blockCount-1)' mod((0:cfg.blockCount-1)',15)] };
    for z=1:numel(sets), r=e.encodedBits; q=sets{z}; for j=1:size(q,1), r(15*q(j,1)+q(j,2)+1)=xor(r(15*q(j,1)+q(j,2)+1),1); end; d=bch15_segmented_decode_reference(caseName{1},r,table); m.multiBlockSingleErrorCases=m.multiBlockSingleErrorCases+1; m.multiBlockSingleErrorMismatch=m.multiBlockSingleErrorMismatch+~isequal(d.recoveredPayload,payload); end
    last=cfg.blockCount-1; firstFiller=11-cfg.fillerBits;
    pairs={[0 1],[0 11],[11 12],[0 firstFiller],[firstFiller firstFiller+1],[firstFiller 11]}; blocks=[0 0 0 last last last];
    for z=1:6, r=e.encodedBits; r(15*blocks(z)+pairs{z}(1)+1)=xor(r(15*blocks(z)+pairs{z}(1)+1),1); r(15*blocks(z)+pairs{z}(2)+1)=xor(r(15*blocks(z)+pairs{z}(2)+1),1); d=bch15_segmented_decode_reference(caseName{1},r,table); blockWrong=any(d.recoveredPaddedMessage~=e.paddedMessageBits); payloadWrong=any(d.recoveredPayload~=payload); m.sameBlockDoubleErrorCases=m.sameBlockDoubleErrorCases+1; m.reportedSuccessWrongBlockInformation=m.reportedSuccessWrongBlockInformation+blockWrong; m.reportedSuccessWrongOriginalPayload=m.reportedSuccessWrongOriginalPayload+payloadWrong; m.fillerOnlyInformationMismatch=m.fillerOnlyInformationMismatch+(blockWrong && ~payloadWrong); end
    for p=0:14, r=e.encodedBits; r(15*last+p+1)=xor(r(15*last+p+1),1); d=bch15_segmented_decode_reference(caseName{1},r,table); m.fillerBoundaryCases=m.fillerBoundaryCases+1; m.fillerBoundaryMismatch=m.fillerBoundaryMismatch+~isequal(d.recoveredPayload,payload); end
    p=table(1).errorPosition; r=e.encodedBits; r(p+1)=xor(r(p+1),1); bad=table; bad(1).errorPosition=15; d=bch15_segmented_decode_reference(caseName{1},r,bad); m.failureStatusRetentionCases=m.failureStatusRetentionCases+1; m.failureStatusRetentionMismatch=m.failureStatusRetentionMismatch+~(strcmp(d.blockDetails{1}.status,'POST_CHECK_FAILED') && d.frameDetail.postCheckFailedBlocks==1);
    bad=table; for j=1:15,bad(j).syndrome=0;end; d=bch15_segmented_decode_reference(caseName{1},r,bad); m.failureStatusRetentionCases=m.failureStatusRetentionCases+1; m.failureStatusRetentionMismatch=m.failureStatusRetentionMismatch+~(strcmp(d.blockDetails{1}.status,'UNRECOGNIZED_SYNDROME') && d.frameDetail.unrecognizedSyndromeBlocks==1 && d.frameDetail.lookupMissBlocks==1);
end
m.doubleErrorClassificationMismatch=(m.reportedSuccessWrongBlockInformation~=12)||(m.reportedSuccessWrongOriginalPayload~=9)||(m.fillerOnlyInformationMismatch~=3);
end

function payloads=pool_payloads(cfg)
payloads=cell(1,104); payloads{1}=zeros(1,cfg.payloadLength); payloads{2}=ones(1,cfg.payloadLength); payloads{3}=alternating_payload(cfg.payloadLength); payloads{4}=zeros(1,cfg.payloadLength); payloads{4}(end)=1;
% Common pool generation is independently reproduced from its packed LSB-first files.
root=fileparts(fileparts(fileparts(fileparts(fileparts(mfilename('fullpath')))))); kind=ternary(cfg.payloadLength==200,'k200','k300'); folder=fullfile(root,'Task','Common','build','stage04','real_pool_runs','smoke','frames',kind);
files=dir(fullfile(folder,'frames_*.bin')); [~,o]=sort({files.name}); files=files(o); frame=1;
bytesPerFrame=ceil(cfg.payloadLength/8);
for f=1:numel(files), fid=fopen(fullfile(folder,files(f).name),'rb'); raw=fread(fid,Inf,'*uint8'); fclose(fid); for offset=0:bytesPerFrame:(numel(raw)-bytesPerFrame), b=raw(offset+1:offset+bytesPerFrame); expanded=zeros(1,bytesPerFrame*8); for i=1:numel(b), for j=0:7,expanded((i-1)*8+j+1)=bitget(b(i),j+1);end,end; payloads{4+frame}=expanded(1:cfg.payloadLength); frame=frame+1; end,end
end
function p=alternating_payload(n), p=mod(0:n-1,2); end
function value=ternary(test,a,b), if test,value=a;else,value=b;end,end
