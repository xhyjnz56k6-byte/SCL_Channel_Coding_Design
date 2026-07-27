function stage10_cfo_formal_matlab_spotcheck(inputCsv, outputCsv, segmentedPath)
addpath(segmentedPath);
o=detectImportOptions(inputCsv,Delimiter=",",TextType="string");
o=setvartype(o,{'caseId','payloadBits','encodedBits','zI','receivedReal','hardBits','cppRecoveredBits'},'string');
t=readtable(inputCsv,o); lookup=bch15_build_lookup_reference();
continuousError=zeros(height(t),1);hardMismatch=zeros(height(t),1);
payloadMismatch=zeros(height(t),1);statusMismatch=zeros(height(t),1);
for row=1:height(t)
 id=char(t.caseId(row));payload=double(char(t.payloadBits(row)))-double('0');
 encoded=double(char(t.encodedBits(row)))-double('0');z=str2double(split(t.zI(row),';'))';
 cppReceived=str2double(split(t.receivedReal(row),';'))';cppHard=double(char(t.hardBits(row)))-double('0');
 n=numel(encoded);k=0:n-1;phase=k*deg2rad(30)/(n-1);
 received=(1-2*encoded).*cos(phase)+t.sigmaDimension(row)*z;hard=received<0;
 continuousError(row)=max(abs(received-cppReceived));hardMismatch(row)=sum(hard~=cppHard);
 recovered=decodePayload(id,hard,lookup);
 cppRecovered=double(char(t.cppRecoveredBits(row)))-double('0');
 payloadMismatch(row)=sum(recovered~=cppRecovered);
 cppSuccess=logical(t.cppTrueSuccess(row));statusMismatch(row)=cppSuccess~=isequal(recovered,payload);
end
caseId=t.caseId;sampleId=t.sampleId;
passed=continuousError<=1e-12 & hardMismatch==0 & payloadMismatch==0 & statusMismatch==0;
writetable(table(caseId,sampleId,continuousError,hardMismatch,payloadMismatch,statusMismatch,passed),outputCsv);
if ~all(passed),error("BLOCKED_STAGE10_CFO_FORMAL_MATLAB_SPOTCHECK");end
fprintf("PASS_STAGE10_CFO_FORMAL_MATLAB_SPOTCHECK\n");
end
function recovered=decodePayload(id,received,lookup)
if contains(id,'_S15')
 old='BCH-S200';if startsWith(id,'K300'),old='BCH-S300';end
 d=bch15_segmented_decode_reference(old,received,lookup);recovered=d.recoveredPayload;return;
end
[n,k,payloads,shortening,lengths]=contract(id);recovered=[];offset=0;
for b=1:numel(payloads)
 part=received(offset+1:offset+lengths(b));d=double(bchdec(gf([zeros(1,shortening(b)),part]),n,k).x);
 recovered=[recovered d(shortening(b)+1:k)];offset=offset+lengths(b); %#ok<AGROW>
end
end
function [n,k,payloads,shortening,lengths]=contract(id)
if contains(id,'M255K207'),n=255;k=207;
 if startsWith(id,'K300'),payloads=[150 150];shortening=[57 57];lengths=[198 198];
 else,payloads=200;shortening=7;lengths=248;end
elseif contains(id,'M511K385'),n=511;k=385;
 if startsWith(id,'K300'),payloads=300;shortening=85;lengths=426;
 else,payloads=200;shortening=185;lengths=326;end
else,error("unsupported spotcheck case");end
end
