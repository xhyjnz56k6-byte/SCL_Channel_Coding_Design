function run_bch_group3_reference(outputPath, detailPath)
% Independent MATLAB GF(2^m) and primitive narrow-sense BCH parameter audit.
if nargin < 1 || nargin > 2, error('one parameter output path and optional detail path required'); end
profiles = {makeProfile('BCH-B200', 200, 255, 207, 7, 8, hex2dec('11D'), 6), ...
            makeProfile('BCH-B300', 300, 511, 421, 121, 9, hex2dec('211'), 10)};
fid = fopen(outputPath, 'w'); if fid < 0, error('cannot open output'); end
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, 'caseName,fieldDegree,primitivePolynomial,generatorPolynomial,generatorDegree,correctionCapability,shorteningLength,shortenedN,shortenedK\n');
for k = 1:numel(profiles)
    p = profiles{k};
    fprintf(fid, '%s,%d,%d,%s,%d,%d,%d,%d,%d\n', p.caseName,p.m,p.primitive,bitsText(p.generator),numel(p.generator)-1,p.t,p.s,p.n-p.s,p.payload);
end
if nargin == 2
    writeDetails(profiles, detailPath);
end
end

function writeDetails(profiles,path)
fid=fopen(path,'w'); if fid<0,error('cannot open detail output');end
cleanup=onCleanup(@() fclose(fid));
fprintf(fid,'caseName,pattern,errorKind,payload,motherCodeword,shortenedCodeword,received,syndromes,locator,rootPositions,correctedShortened,decodedPayload,status\n');
for k=1:numel(profiles)
 p=profiles{k}; tables=gfTables(p.m,p.primitive);
 for pattern=0:207
  payload=vectorFor(p.payload,pattern); [mother,shortened]=encodeWord(p,payload);
  for error=0:6
   received=shortened; name='NONE';
   if error==1, received(1)=1-received(1); name='FIRST'; end
   if error==2, received(end)=1-received(end); name='LAST'; end
   if error==3, name='T'; for j=0:(p.t-1), index=mod(j*29+7,numel(received))+1; received(index)=1-received(index); end, end
   if error>=4, if error==4, name='T_PLUS_1'; weight=p.t+1; elseif error==5, name='T_PLUS_2'; weight=p.t+2; else, name='HIGH_WEIGHT'; weight=p.t+5; end, for j=0:(weight-1), index=mod(j*29+7,numel(received))+1; received(index)=1-received(index); end, end
   d=decodeWord(p,tables,received);
   fprintf(fid,'%s,%d,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n',p.caseName,pattern,name,bitsText(payload),bitsText(mother),bitsText(shortened),bitsText(received),numberText(d.syndromes),numberText(d.locator),positionText(d.roots),bitsText(d.corrected),bitsText(d.payload),d.status);
  end
 end
end
end

function bits=vectorFor(length,pattern)
bits=zeros(1,length);
for i=0:(length-1)
 if pattern==1, bits(i+1)=1; elseif pattern==2, bits(i+1)=mod(i,2); elseif pattern==3, bits(i+1)=mod(i+1,2); elseif pattern>=4, bits(i+1)=double(mod(i*37+pattern*19+11,101)<50); end
end
end

function [mother,shortened]=encodeWord(p,payload)
info=[zeros(1,p.s),payload]; division=[info,zeros(1,numel(p.generator)-1)];
for i=1:numel(info)
 if division(i)~=0, division(i:(i+numel(p.generator)-1))=xor(division(i:(i+numel(p.generator)-1)),p.generator); end
end
mother=[info,division((end-numel(p.generator)+2):end)]; shortened=mother((p.s+1):end);
end

function d=decodeWord(p,t,received)
mother=[zeros(1,p.s),received]; syndrome=allSyndromes(mother,p,t);
if all(syndrome==0), d=struct('syndromes',syndrome,'locator',uint16(1),'roots',[],'corrected',received,'payload',received(1:p.payload),'status','NO_ERROR');return;end
locator=bm(syndrome,t); degree=numel(locator)-1; roots=[];
if degree>p.t, status='LOCATOR_DEGREE_EXCEEDS_T'; else
 for index=1:numel(mother)
  exponent=numel(mother)-index;
  if evaluate(locator,alphaPower(-exponent,t),t)==0, roots(end+1)=index-1; end %#ok<AGROW>
 end
 if numel(roots)~=degree, status='INVALID_ROOT_COUNT'; elseif any(roots<p.s), status='ROOT_IN_SHORTENED_PREFIX'; else
  for index=roots+1, mother(index)=1-mother(index); end
  if all(allSyndromes(mother,p,t)==0), status='CORRECTED'; else, status='POST_SYNDROME_NONZERO'; end
 end
end
d=struct('syndromes',syndrome,'locator',locator,'roots',roots,'corrected',mother((p.s+1):end),'payload',mother((p.s+1):p.k),'status',status);
end

function s=allSyndromes(word,p,t)
s=zeros(1,2*p.t,'uint16');
for j=1:(2*p.t)
 for index=1:numel(word)
  if word(index)~=0, s(j)=bitxor(s(j),alphaPower(j*(numel(word)-index),t)); end
 end
end
end

function locator=bm(sequence,t)
locator=uint16(1); backup=uint16(1); length=0; shift=1; last=uint16(1);
for n=0:(numel(sequence)-1)
 discrepancy=sequence(n+1);
 for i=1:length, discrepancy=bitxor(discrepancy,mul(locator(i+1),sequence(n-i+1),t)); end
 if discrepancy==0, shift=shift+1; continue; end
 previous=locator; if numel(locator)<numel(backup)+shift, locator(end+1:(numel(backup)+shift))=0; end
 scale=divide(discrepancy,last,t);
 for i=1:numel(backup), locator(i+shift)=bitxor(locator(i+shift),mul(scale,backup(i),t)); end
 if 2*length<=n, length=n+1-length; backup=previous; last=discrepancy; shift=1; else, shift=shift+1; end
end
locator=locator(1:(length+1));
end

function z=divide(a,b,t)
if b==0,error('GF divide zero');end
if a==0,z=uint16(0);else,z=t.anti(mod(t.log(double(a)+1)-t.log(double(b)+1),t.q-1)+1);end
end
function z=alphaPower(e,t), z=t.anti(mod(e,t.q-1)+1); end
function z=evaluate(poly,x,t)
z=uint16(0); for i=numel(poly):-1:1, z=bitxor(mul(z,x,t),poly(i)); end
end
function s=numberText(values), s=strjoin(arrayfun(@num2str,double(values),'UniformOutput',false),':'); end
function s=positionText(values), s=strjoin(arrayfun(@num2str,values,'UniformOutput',false),':'); end

function p = makeProfile(name,payload,n,k,s,m,primitive,t)
tables = gfTables(m,primitive); roots = [];
for r=1:(2*t)
    x = mod(r,n); start=x;
    while true
        roots(end+1)=x; %#ok<AGROW>
        x=mod(2*x,n); if x==start, break; end
    end
end
roots=unique(roots); poly=uint16(1);
for r=roots
    a=tables.anti(r+1); next=zeros(1,numel(poly)+1,'uint16');
    for i=1:numel(poly)
        next(i)=bitxor(next(i), mul(poly(i),a,tables)); next(i+1)=bitxor(next(i+1),poly(i));
    end
    poly=next;
end
if any(poly>1), error('generator is not binary'); end
p=struct('caseName',name,'payload',payload,'n',n,'k',k,'s',s,'m',m,'primitive',primitive,'t',t,'generator',fliplr(double(poly)));
if numel(p.generator)-1 ~= n-k, error('generator degree mismatch'); end
end

function tables=gfTables(m,primitive)
q=2^m; anti=zeros(1,q-1,'uint16'); log=-ones(1,q); value=uint32(1);
for i=0:q-2
    if log(double(value)+1)~=-1, error('not primitive'); end
    anti(i+1)=uint16(value); log(double(value)+1)=i; value=bitshift(value,1);
    if bitand(value,uint32(q))~=0, value=bitxor(value,uint32(primitive)); end
    value=bitand(value,uint32(q-1));
end
if value~=1, error('not primitive'); end
tables=struct('q',q,'anti',anti,'log',log);
end

function z=mul(a,b,t)
if a==0 || b==0, z=uint16(0); return; end
z=t.anti(mod(t.log(double(a)+1)+t.log(double(b)+1),t.q-1)+1);
end

function s=bitsText(bits)
s=char(bits + '0');
end
