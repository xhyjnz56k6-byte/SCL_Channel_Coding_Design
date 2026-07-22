function run_bch_group3_gf_detail(outputPath)
fid=fopen(outputPath,'w');if fid<0,error('cannot open output');end
cleanup=onCleanup(@()fclose(fid));fprintf(fid,'fieldDegree,operation,a,b,result\n');
for item={8,hex2dec('11D');9,hex2dec('211')}'; m=item{1};t=tables(m,item{2});period=t.q-1;
 for e=0:period-1,fprintf(fid,'%d,alpha,%d,,%d\n',m,e,t.anti(e+1));end
 for a=1:period,fprintf(fid,'%d,log,%d,,%d\n',m,a,t.log(a+1));fprintf(fid,'%d,inverse,%d,,%d\n',m,a,divide(1,a,t));end
 for i=0:255,a=mod(i*37+11,t.q);b=mod(i*53+7,period)+1;fprintf(fid,'%d,multiply,%d,%d,%d\n',m,a,b,mul(a,b,t));fprintf(fid,'%d,divide,%d,%d,%d\n',m,a,b,divide(a,b,t));fprintf(fid,'%d,evaluate,%d,%d,%d\n',m,a,b,evaluate(uint16([1,a,b]),b,t));end
end
end
function t=tables(m,p),q=2^m;t.q=q;t.anti=zeros(1,q-1,'uint16');t.log=-ones(1,q);v=uint32(1);for i=0:q-2,t.anti(i+1)=uint16(v);t.log(double(v)+1)=i;v=bitshift(v,1);if bitand(v,uint32(q)),v=bitxor(v,uint32(p));end;v=bitand(v,uint32(q-1));end;end
function z=mul(a,b,t),if a==0||b==0,z=uint16(0);else,z=t.anti(mod(t.log(double(a)+1)+t.log(double(b)+1),t.q-1)+1);end;end
function z=divide(a,b,t),if a==0,z=uint16(0);else,z=t.anti(mod(t.log(double(a)+1)-t.log(double(b)+1),t.q-1)+1);end;end
function z=evaluate(c,x,t),z=uint16(0);for i=numel(c):-1:1,z=bitxor(mul(z,x,t),c(i));end;end
