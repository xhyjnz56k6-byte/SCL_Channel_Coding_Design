stageDir = fileparts(fileparts(mfilename('fullpath')));
inputPath = fullfile(stageDir, 'results', 'stage02_trellis_encoder_cpp_matlab_vectors.csv');
outputPath = fullfile(stageDir, 'results', 'stage02_trellis_encoder_matlab_comparison.csv');
trellisInputPath = fullfile(stageDir, 'results', 'stage02_trellis_encoder_cpp_trellis.csv');
trellisOutputPath = fullfile(stageDir, 'results', 'stage02_trellis_encoder_matlab_trellis_comparison.csv');

options = detectImportOptions(inputPath, 'TextType', 'string');
options = setvartype(options, {'inputBits', 'cppMotherBits'}, 'string');
inputTable = readtable(inputPath, options);
trellis = poly2trellis(7, [171 133]);

vectorId = inputTable.vectorId;
bitMismatch = zeros(height(inputTable), 1);
matlabMotherBits = strings(height(inputTable), 1);

for row = 1:height(inputTable)
    inputText = char(inputTable.inputBits(row));
    cppText = char(inputTable.cppMotherBits(row));
    inputBits = double(inputText) - double('0');
    cppBits = double(cppText) - double('0');
    encoded = convenc(inputBits, trellis);
    bitMismatch(row) = sum(encoded ~= cppBits);
    matlabMotherBits(row) = string(char(encoded + double('0')));
end

status = repmat("PASS", height(inputTable), 1);
status(bitMismatch ~= 0) = "FAIL";
comparison = table(vectorId, inputTable.inputBits, inputTable.cppMotherBits, ...
    matlabMotherBits, bitMismatch, status, ...
    'VariableNames', {'vectorId', 'inputBits', 'cppMotherBits', ...
    'matlabMotherBits', 'bitMismatch', 'status'});
writetable(comparison, outputPath);

if any(bitMismatch ~= 0)
    error('Stage02 MATLAB comparison mismatch');
end

cppTrellis = readtable(trellisInputPath);
matlabNextState = zeros(height(cppTrellis), 1);
matlabOutputDecimal = zeros(height(cppTrellis), 1);
nextStateMismatch = zeros(height(cppTrellis), 1);
outputMismatch = zeros(height(cppTrellis), 1);
for row = 1:height(cppTrellis)
    stateIndex = cppTrellis.state(row) + 1;
    inputIndex = cppTrellis.inputBit(row) + 1;
    matlabNextState(row) = trellis.nextStates(stateIndex, inputIndex);
    matlabOutputDecimal(row) = trellis.outputs(stateIndex, inputIndex);
    nextStateMismatch(row) = matlabNextState(row) ~= cppTrellis.nextState(row);
    outputMismatch(row) = matlabOutputDecimal(row) ~= cppTrellis.outputDecimal(row);
end
trellisStatus = repmat("PASS", height(cppTrellis), 1);
trellisStatus(nextStateMismatch ~= 0 | outputMismatch ~= 0) = "FAIL";
trellisComparison = table(cppTrellis.state, cppTrellis.inputBit, ...
    cppTrellis.nextState, matlabNextState, cppTrellis.outputDecimal, ...
    matlabOutputDecimal, nextStateMismatch, outputMismatch, trellisStatus, ...
    'VariableNames', {'state', 'inputBit', 'cppNextState', ...
    'matlabNextState', 'cppOutputDecimal', 'matlabOutputDecimal', ...
    'nextStateMismatch', 'outputMismatch', 'status'});
writetable(trellisComparison, trellisOutputPath);
if any(nextStateMismatch ~= 0) || any(outputMismatch ~= 0)
    error('Stage02 MATLAB trellis table mismatch');
end
disp('PASS_STAGE02_MATLAB_POLY2TRELLIS_CONVENC');
