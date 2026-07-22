function run_bch_group3_toolbox_reference(outputPath)
% Communications Toolbox terminal parameter reference; no C++ output is read.
fid=fopen(outputPath,'w'); if fid<0,error('cannot open output');end
cleanup=onCleanup(@() fclose(fid));
fprintf(fid,'caseName,motherN,motherK,toolboxT,generatorPolynomial\n');
cases={'BCH-B200',255,207;'BCH-B300',511,421};
for i=1:size(cases,1)
 [g,t]=bchgenpoly(cases{i,2},cases{i,3});
 bits=char(double(g.x)+'0');
 fprintf(fid,'%s,%d,%d,%d,%s\n',cases{i,1},cases{i,2},cases{i,3},t,bits);
end
end
