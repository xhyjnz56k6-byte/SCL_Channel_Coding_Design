stageDir=fileparts(fileparts(mfilename('fullpath')));
inPath=fullfile(stageDir,'results','stage06_puncturing_cpp_matlab_vectors.csv');
outPath=fullfile(stageDir,'results','stage06_puncturing_matlab_comparison.csv');
opts=detectImportOptions(inPath,'TextType','string','Delimiter',',');
opts=setvartype(opts,{'patternId','keepMask','payloadBits','puncturedBits','hardDecodedPayload','softDecodedPayload'},'string');
t=readtable(inPath,opts);
trellis=poly2trellis(7,[171 133]);
punctureMismatch=zeros(height(t),1);
hardPayloadMismatch=zeros(height(t),1);
softPayloadMismatch=zeros(height(t),1);
for row=1:height(t)
    payload=double(char(t.payloadBits(row)))-double('0');
    codec=[payload zeros(1,6)];
    mother=convenc(codec,trellis);
    pattern=double(char(t.keepMask(row)))-double('0');
    repeated=repmat(pattern,1,ceil(length(mother)/length(pattern)));
    matlabPunctured=mother(logical(repeated(1:length(mother))));
    cppPunctured=double(char(t.puncturedBits(row)))-double('0');
    punctureMismatch(row)=sum(matlabPunctured~=cppPunctured);
    hardDecoded=vitdec(matlabPunctured,trellis,35,'term','hard',pattern');
    softInput=1-2*matlabPunctured;
    softDecoded=vitdec(softInput,trellis,35,'term','unquant',pattern');
    hardPayloadMismatch(row)=sum(hardDecoded(1:300)~=payload);
    softPayloadMismatch(row)=sum(softDecoded(1:300)~=payload);
end
status=repmat("PASS",height(t),1);
status(punctureMismatch~=0|hardPayloadMismatch~=0|softPayloadMismatch~=0)="FAIL";
comparison=table(t.patternId,punctureMismatch,hardPayloadMismatch,softPayloadMismatch,status, ...
    'VariableNames',{'patternId','punctureMismatch','hardPayloadMismatch','softPayloadMismatch','status'});
writetable(comparison,outPath);
if any(status~="PASS"), error('Stage06 MATLAB puncture mismatch'); end
disp('PASS_STAGE06_MATLAB_PUNCTURING');
