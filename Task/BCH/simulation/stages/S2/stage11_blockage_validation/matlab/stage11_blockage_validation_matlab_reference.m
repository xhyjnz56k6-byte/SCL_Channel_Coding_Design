function stage11_blockage_validation_matlab_reference(stage_dir)
t=readtable(fullfile(stage_dir,'results','stage11_blockage_validation_fixed_vectors.csv'));
n=height(t); isBlocked=zeros(n,1); received=zeros(n,1); hardBit=zeros(n,1);
for i=1:n
 k=t.k(i); isBlocked(i)=(k>=t.start(i) && k<t.start(i)+t.length(i));
 gain=1; if isBlocked(i), gain=t.amplitude(i); end
 received(i)=gain*t.bpsk(i)+t.noise(i); hardBit(i)=received(i)<0;
end
out=table(t.vectorId,t.k,isBlocked,received,hardBit, ...
 'VariableNames',{'vectorId','k','isBlocked','received','hardBit'});
writetable(out,fullfile(stage_dir,'results','stage11_blockage_validation_matlab_outputs.csv'));
fprintf('PASS_STAGE11_BLOCKAGE_VALIDATION_MATLAB\n');
end
