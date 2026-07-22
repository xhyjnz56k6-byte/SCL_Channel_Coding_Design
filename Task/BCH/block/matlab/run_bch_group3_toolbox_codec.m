function run_bch_group3_toolbox_codec(k200,k300,outputPath)
fid=fopen(outputPath,'w');if fid<0,error('cannot open output');end;c=onCleanup(@()fclose(fid));fprintf(fid,'caseName,fixedFrames,encoderMismatch,singleErrorCases,decodedPayloadMismatch\n');
runCase('BCH-B200',k200,200,255,207,7,fid);runCase('BCH-B300',k300,300,511,421,121,fid);
end
function runCase(name,manifestPath,payloadLength,n,k,s,fid)
m=jsondecode(fileread(manifestPath));directory=fileparts(manifestPath);packed=[];for i=1:numel(m.shards),f=fopen(fullfile(directory,m.shards(i).fileName),'rb');packed=[packed;fread(f,inf,'uint8=>uint8')];fclose(f);end
[g,~]=bchgenpoly(n,k);gen=double(g.x);r=n-k;encoderMismatch=0;decodeMismatch=0;singleCases=0;
for frame=0:7
 block=packed(frame*m.bytesPerFrame+1:(frame+1)*m.bytesPerFrame);payload=zeros(1,payloadLength);for b=0:payloadLength-1,payload(b+1)=bitget(block(floor(b/8)+1),mod(b,8)+1);end
 info=[zeros(1,s),payload];toolbox=double(bchenc(gf(info),n,k).x);division=[info,zeros(1,r)];for i=1:k,if division(i),division(i:i+r)=xor(division(i:i+r),gen);end,end;self=[info,division(end-r+1:end)];encoderMismatch=encoderMismatch+~isequal(toolbox,self);
 short=toolbox(s+1:end);for pos=1:numel(short),received=[zeros(1,s),short];received(s+pos)=1-received(s+pos);decoded=double(bchdec(gf(received),n,k).x);decodeMismatch=decodeMismatch+~isequal(decoded(s+1:k),payload);singleCases=singleCases+1;end
end
fprintf(fid,'%s,8,%d,%d,%d\n',name,encoderMismatch,singleCases,decodeMismatch);
end
