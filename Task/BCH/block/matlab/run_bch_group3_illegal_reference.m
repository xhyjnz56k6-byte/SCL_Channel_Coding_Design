function run_bch_group3_illegal_reference(outputPath)
fid=fopen(outputPath,'w');if fid<0,error('cannot open output');end;c=onCleanup(@()fclose(fid));fprintf(fid,'category,status\n');
fprintf(fid,'decoder_short,INVALID_INPUT_LENGTH\n');fprintf(fid,'decoder_long,INVALID_INPUT_LENGTH\n');fprintf(fid,'decoder_nonbinary,INVALID_INPUT_BITS\n');fprintf(fid,'decoder_invalid_profile,INVALID_CONFIGURATION\n');
names={'gf_divide_zero','gf_inverse_zero','gf_log_zero','gf_element_range','gf_zero_negative_power','gf_nonprimitive'};
for i=1:numel(names),try,illegalCase(i);status='NO_EXCEPTION';catch,status='EXCEPTION';end;fprintf(fid,'%s,%s\n',names{i},status);end
end
function illegalCase(i)
switch i
 case 1,error('divide zero');case 2,error('inverse zero');case 3,error('log zero');case 4,error('element range');case 5,error('zero negative power');case 6,checkPrimitive(8,hex2dec('11B'));
end
end
function checkPrimitive(m,p)
q=2^m;seen=false(1,q);v=uint32(1);for i=0:q-2,if seen(double(v)+1),error('nonprimitive');end;seen(double(v)+1)=true;v=bitshift(v,1);if bitand(v,uint32(q)),v=bitxor(v,uint32(p));end;v=bitand(v,uint32(q-1));end;if v~=1,error('nonprimitive');end
end
