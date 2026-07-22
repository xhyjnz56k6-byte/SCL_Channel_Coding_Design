function run_bch_group3_pool_encoder(k200,k300,outputPath)
fid=fopen(outputPath,'w'); if fid<0,error('cannot open output');end
cleanup=onCleanup(@() fclose(fid));
fprintf(fid,'caseName,frameIndex,payload,motherInformation,parity,motherCodeword,shortenedCodeword,remainder,divisible\n');
runCase('BCH-B200',k200,200,255,207,7,fid); runCase('BCH-B300',k300,300,511,421,121,fid);
end
function runCase(name,manifestPath,payloadLength,n,k,s,fid)
m=jsondecode(fileread(manifestPath)); directory=fileparts(manifestPath); packed=[];
for i=1:numel(m.shards), f=fopen(fullfile(directory,m.shards(i).fileName),'rb'); packed=[packed;fread(f,inf,'uint8=>uint8')]; fclose(f); end
[g,~]=bchgenpoly(n,k); gen=double(g.x); r=n-k; bytes=m.bytesPerFrame;
for frame=0:99
 block=packed(frame*bytes+1:(frame+1)*bytes); payload=zeros(1,payloadLength);
 for b=0:payloadLength-1,payload(b+1)=bitget(block(floor(b/8)+1),mod(b,8)+1);end
 info=[zeros(1,s),payload]; division=[info,zeros(1,r)];
 for i=1:numel(info),if division(i)~=0,division(i:i+r)=xor(division(i:i+r),gen);end,end
 parity=division(end-r+1:end); mother=[info,parity]; short=mother(s+1:end); verify=mother;
 for i=1:k,if verify(i)~=0,verify(i:i+r)=xor(verify(i:i+r),gen);end,end
 fprintf(fid,'%s,%d,%s,%s,%s,%s,%s,%s,%d\n',name,frame,bits(payload),bits(info),bits(parity),bits(mother),bits(short),bits(verify(end-r+1:end)),all(verify(end-r+1:end)==0));
end
end
function s=bits(x),s=char(x+'0');end
