function run_bch_s2_burst_redesign_reference(inputCsv, outputCsv)
% Independent hard-bit burst/interleaver/BCH reference for S2-07A..D.
addpath(fullfile(fileparts(mfilename('fullpath')), '..', '..', '..', 'segmented', 'matlab'));
opts = detectImportOptions(inputCsv,'Delimiter',',','VariableNamingRule','preserve');
opts = setvartype(opts,opts.VariableNames,'string');
d = readtable(inputCsv,opts);
numeric = ["frameIndex","burstLength","burstStart","cppReportedSuccess", ...
    "cppTrueSuccess","cppMiscorrection","cppDecoderFailure", ...
    "cppPostDeinterleaveErrorWeight"];
for name=numeric, d.(name)=str2double(d.(name)); end
if height(d) ~= 9040, error('BCH:S207Input','expected 9040 rows'); end
lookup=bch15_build_lookup_reference();
stages=["S2-07A","S2-07B","S2-07C","S2-07D"];
cases=["BCH-S200","BCH-B200","BCH-S300","BCH-B300","BCH-B300-426"];
summary=table();
for stage=stages
 for caseName=cases
  selected=d(d.stage==stage & d.caseName==caseName,:);
  if isempty(selected), continue; end
  encodedMismatch=0; burstMismatch=0; deinterleaveMismatch=0;
  payloadMismatch=0; frameMismatch=0; statusMismatch=0;
  permutationMismatch=0; weightMismatch=0;
  for row=1:height(selected)
   payload=bits(selected.payloadBits(row));
   encodedCpp=bits(selected.encodedBits(row));
   encoded=encodeCase(caseName,payload);
   encodedMismatch=encodedMismatch+sum(encoded~=encodedCpp);
   p=numbers(selected.permutation(row))+1;
   invp=numbers(selected.inversePermutation(row))+1;
   permutationMismatch=permutationMismatch+(numel(unique(p))~=numel(p));
   permutationMismatch=permutationMismatch+sum(invp(p)~=(1:numel(p)));
   transmitted=encoded(p);
   first=selected.burstStart(row)+1;
   last=first+selected.burstLength(row)-1;
   if selected.burstLength(row)>0, transmitted(first:last)=1-transmitted(first:last); end
   burstMismatch=burstMismatch+sum(transmitted~=bits(selected.cppTransmittedDamagedBits(row)));
   received=transmitted(invp);
   deinterleaveMismatch=deinterleaveMismatch+sum(received~=bits(selected.cppDeinterleavedBits(row)));
   weight=sum(received~=encoded);
   weightMismatch=weightMismatch+(weight~=selected.burstLength(row));
   weightMismatch=weightMismatch+(weight~=selected.cppPostDeinterleaveErrorWeight(row));
   [decoded,reported]=decodeCase(caseName,received,lookup);
   payloadMismatch=payloadMismatch+sum(decoded~=bits(selected.cppDecodedPayload(row)));
   trueSuccess=all(decoded==payload); frameMismatch=frameMismatch+(trueSuccess~=logical(selected.cppTrueSuccess(row)));
   misc=reported && ~trueSuccess; failure=~reported;
   statusMismatch=statusMismatch+(reported~=logical(selected.cppReportedSuccess(row))) + ...
      (misc~=logical(selected.cppMiscorrection(row))) + ...
      (failure~=logical(selected.cppDecoderFailure(row)));
  end
  gate="PASS";
  total=encodedMismatch+burstMismatch+deinterleaveMismatch+payloadMismatch+ ...
      frameMismatch+statusMismatch+permutationMismatch+weightMismatch;
  if total~=0, gate="FAIL"; end
  summary=[summary; table(stage,caseName,height(selected),encodedMismatch, ...
      burstMismatch,deinterleaveMismatch,payloadMismatch,frameMismatch, ...
      statusMismatch,permutationMismatch,weightMismatch,gate)]; %#ok<AGROW>
 end
end
writetable(summary,outputCsv);
if any(summary.gate~="PASS"), error('BCH:S207Mismatch','reference mismatch'); end
fprintf('PASS_BCH_S2_07_MATLAB_BURST_REFERENCE frames=%d\n',sum(summary.Var3));
end

function value=bits(text), value=double(char(text)=='1'); end
function value=numbers(text), value=str2double(split(string(text),';')).'; end
function encoded=encodeCase(name,payload)
 if name=="BCH-S200", encoded=official_encode_s200(payload);
 elseif name=="BCH-S300"
  padded=[payload zeros(1,8)]; segments=reshape(padded.',11,[]).';
  code=double(bchenc(gf(segments),15,11,'end').x); encoded=reshape(code.',420,[]).';
 else
  if name=="BCH-B200", n=255;k=207;s=7;
  elseif name=="BCH-B300", n=511;k=421;s=121;
  else, n=511;k=385;s=85; end
  code=double(bchenc(gf([zeros(1,s) payload]),n,k,'end').x); encoded=code(s+1:n);
 end
end
function [payload,reported]=decodeCase(name,hard,lookup)
 if name=="BCH-S200" || name=="BCH-S300"
  decoded=bch15_segmented_decode_reference(char(name),hard,lookup);
  payload=decoded.recoveredPayload;
  reported=decoded.frameDetail.lookupMissBlocks==0 && decoded.frameDetail.postCheckFailedBlocks==0;
 else
  if name=="BCH-B200", n=255;k=207;s=7;
  elseif name=="BCH-B300", n=511;k=421;s=121;
  else, n=511;k=385;s=85; end
  [decoded,errors]=bchdec(gf([zeros(1,s) hard]),n,k,'end');
  payload=double(decoded.x(s+1:k)); reported=errors>=0;
 end
end
