function stage09_cfo_validation_matlab_reference(stage_dir)
fixed_path = fullfile(stage_dir, 'results', 'stage09_cfo_validation_fixed_vectors.csv');
out_path = fullfile(stage_dir, 'results', 'stage09_cfo_validation_matlab_outputs.csv');
t = readtable(fixed_path);
n = height(t);
phaseRad = zeros(n,1);
realValue = zeros(n,1);
imagValue = zeros(n,1);
hardBit = zeros(n,1);
for i = 1:n
    k = t.k(i); % CSV/C++ zero-based symbol index; MATLAB row i uses k=i-1.
    if t.encodedLength(i) == 1
        delta = 0;
    else
        delta = deg2rad(t.targetEndPhaseDeg(i)) / (t.encodedLength(i)-1);
    end
    phaseRad(i) = k * delta;
    realValue(i) = t.bpsk(i)*cos(phaseRad(i)) + t.noiseI(i);
    imagValue(i) = t.bpsk(i)*sin(phaseRad(i)) + t.noiseQ(i);
    hardBit(i) = realValue(i) < 0;
end
out = table(t.vectorId,t.k,phaseRad,realValue,imagValue,hardBit, ...
    'VariableNames',{'vectorId','k','phaseRad','realValue','imagValue','hardBit'});
writetable(out,out_path);
fprintf('PASS_STAGE09_CFO_VALIDATION_MATLAB\n');
end
