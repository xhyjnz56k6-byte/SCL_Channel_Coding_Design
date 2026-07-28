stageDir = fileparts(fileparts(mfilename('fullpath')));
resultDir = fullfile(stageDir, 'results');
vectorPath = fullfile(resultDir, 'stage05_matlab_reference_cpp_vectors.csv');
trellisPath = fullfile(resultDir, 'stage05_matlab_reference_cpp_trellis.csv');
outputPath = fullfile(resultDir, 'stage05_matlab_reference_comparison.csv');
opts = detectImportOptions(vectorPath, 'TextType', 'string', 'Delimiter', ',');
opts = setvartype(opts, {'payloadBits','codecInputBits','motherBits','receivedSymbols', ...
    'llr','hardDecodedPayload','softDecodedPayload'}, 'string');
t = readtable(vectorPath, opts);
cppTrellis = readtable(trellisPath);
trellis = poly2trellis(7, [171 133]);

trellisNextMismatch = 0;
trellisOutputMismatch = 0;
for row = 1:height(cppTrellis)
    s = cppTrellis.state(row) + 1;
    u = cppTrellis.inputBit(row) + 1;
    trellisNextMismatch = trellisNextMismatch + ...
        (trellis.nextStates(s,u) ~= cppTrellis.nextState(row));
    trellisOutputMismatch = trellisOutputMismatch + ...
        (trellis.outputs(s,u) ~= cppTrellis.outputDecimal(row));
end

encodeMismatch = zeros(height(t),1);
finalStateMismatch = zeros(height(t),1);
hardPayloadMismatch = zeros(height(t),1);
softSymbolPayloadMismatch = zeros(height(t),1);
softLlrPayloadMismatch = zeros(height(t),1);
for row = 1:height(t)
    payload = double(char(t.payloadBits(row))) - double('0');
    codecInput = double(char(t.codecInputBits(row))) - double('0');
    mother = double(char(t.motherBits(row))) - double('0');
    received = str2double(split(t.receivedSymbols(row), ';'))';
    llr = str2double(split(t.llr(row), ';'))';
    [matlabMother, matlabFinalState] = convenc(codecInput, trellis);
    encodeMismatch(row) = sum(matlabMother ~= mother);
    finalStateMismatch(row) = matlabFinalState ~= t.finalState(row);
    hardInput = received < 0;
    hardDecoded = vitdec(hardInput, trellis, 35, 'term', 'hard');
    softSymbolsDecoded = vitdec(received, trellis, 35, 'term', 'unquant');
    softLlrDecoded = vitdec(llr, trellis, 35, 'term', 'unquant');
    hardPayloadMismatch(row) = sum(hardDecoded(1:300) ~= payload);
    softSymbolPayloadMismatch(row) = sum(softSymbolsDecoded(1:300) ~= payload);
    softLlrPayloadMismatch(row) = sum(softLlrDecoded(1:300) ~= payload);
end
status = repmat("PASS",height(t),1);
status(encodeMismatch~=0 | finalStateMismatch~=0 | hardPayloadMismatch~=0 | ...
    softSymbolPayloadMismatch~=0 | softLlrPayloadMismatch~=0) = "FAIL";
comparison = table(t.vectorId, encodeMismatch, finalStateMismatch, ...
    hardPayloadMismatch, softSymbolPayloadMismatch, softLlrPayloadMismatch, status, ...
    'VariableNames', {'vectorId','encodeMismatch','finalStateMismatch', ...
    'hardPayloadMismatch','softSymbolPayloadMismatch','softLlrPayloadMismatch','status'});
writetable(comparison, outputPath);
if trellisNextMismatch ~= 0 || trellisOutputMismatch ~= 0 || any(status ~= "PASS")
    error('Stage05 C++/MATLAB reference mismatch');
end
disp('PASS_STAGE05_CC_MATLAB_REFERENCE');
