stageDir = fileparts(fileparts(mfilename('fullpath')));
inputPath = fullfile(stageDir, 'results', 'stage04_soft_viterbi_cpp_matlab_vectors.csv');
outputPath = fullfile(stageDir, 'results', 'stage04_soft_viterbi_matlab_comparison.csv');
opts = detectImportOptions(inputPath, 'TextType', 'string', 'Delimiter', ',');
opts = setvartype(opts, {'receivedSymbols', 'cppCodecInputBits', 'cppPayloadBits'}, 'string');
t = readtable(inputPath, opts);
trellis = poly2trellis(7, [171 133]);
payloadMismatch = zeros(height(t), 1);
codecInputMismatch = zeros(height(t), 1);
for row = 1:height(t)
    received = str2double(split(t.receivedSymbols(row), ';'))';
    cppCodec = double(char(t.cppCodecInputBits(row))) - double('0');
    cppPayload = double(char(t.cppPayloadBits(row))) - double('0');
    decoded = vitdec(received, trellis, 35, 'term', 'unquant');
    codecInputMismatch(row) = sum(decoded ~= cppCodec);
    payloadMismatch(row) = sum(decoded(1:300) ~= cppPayload);
end
status = repmat("PASS", height(t), 1);
status(codecInputMismatch ~= 0 | payloadMismatch ~= 0) = "FAIL";
comparison = table(t.vectorId, codecInputMismatch, payloadMismatch, status, ...
    'VariableNames', {'vectorId','codecInputMismatch','payloadMismatch','status'});
writetable(comparison, outputPath);
if any(codecInputMismatch ~= 0) || any(payloadMismatch ~= 0)
    error('Stage04 MATLAB unquantized mismatch');
end
disp('PASS_STAGE04_MATLAB_VITDEC_UNQUANT');
