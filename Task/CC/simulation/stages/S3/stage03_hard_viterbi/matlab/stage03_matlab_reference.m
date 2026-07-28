stageDir = fileparts(fileparts(mfilename('fullpath')));
inputPath = fullfile(stageDir, 'results', 'stage03_hard_viterbi_cpp_matlab_vectors.csv');
outputPath = fullfile(stageDir, 'results', 'stage03_hard_viterbi_matlab_comparison.csv');
options = detectImportOptions(inputPath, 'TextType', 'string');
options = setvartype(options, {'receivedMotherBits', 'cppCodecInputBits', 'cppPayloadBits'}, 'string');
inputTable = readtable(inputPath, options);
trellis = poly2trellis(7, [171 133]);

codecInputMismatch = zeros(height(inputTable), 1);
payloadMismatch = zeros(height(inputTable), 1);
matlabCodecInputBits = strings(height(inputTable), 1);
for row = 1:height(inputTable)
    receivedText = char(inputTable.receivedMotherBits(row));
    cppCodecText = char(inputTable.cppCodecInputBits(row));
    cppPayloadText = char(inputTable.cppPayloadBits(row));
    received = double(receivedText) - double('0');
    decoded = vitdec(received, trellis, 35, 'term', 'hard');
    matlabCodecInputBits(row) = string(char(decoded + double('0')));
    codecInputMismatch(row) = sum(decoded ~= (double(cppCodecText) - double('0')));
    payloadMismatch(row) = sum(decoded(1:300) ~= (double(cppPayloadText) - double('0')));
end
status = repmat("PASS", height(inputTable), 1);
status(codecInputMismatch ~= 0 | payloadMismatch ~= 0) = "FAIL";
comparison = table(inputTable.vectorId, matlabCodecInputBits, ...
    codecInputMismatch, payloadMismatch, status, ...
    'VariableNames', {'vectorId', 'matlabCodecInputBits', ...
    'codecInputMismatch', 'payloadMismatch', 'status'});
writetable(comparison, outputPath);
if any(codecInputMismatch ~= 0) || any(payloadMismatch ~= 0)
    error('Stage03 MATLAB vitdec hard mismatch');
end
disp('PASS_STAGE03_MATLAB_VITDEC_HARD');
