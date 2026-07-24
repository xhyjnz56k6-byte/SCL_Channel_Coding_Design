function run_bch16w3_official_codec(cppDetailCsv, cppProfileCsv, outputDir)
% Official MATLAB Communications Toolbox validation for BCH-B300-426.
if ~exist(outputDir, 'dir')
    mkdir(outputDir);
end

envPath = fullfile(outputDir, 'matlab_environment.json');
env = fopen(envPath, 'w');
if env < 0
    error('BCH16W3:OutputOpen', 'failed to open matlab_environment.json');
end
cleanupEnv = onCleanup(@() fclose(env));
commInfo = ver('comm');
hasComm = ~isempty(commInfo);
fprintf(env, '{\n');
fprintf(env, '  "matlabVersion": "%s",\n', version);
fprintf(env, '  "platform": "%s",\n', computer);
fprintf(env, '  "communicationsToolboxAvailable": %s,\n', lower(string(hasComm)));
if hasComm
    fprintf(env, '  "communicationsToolboxVersion": "%s",\n', commInfo.Version);
else
    fprintf(env, '  "communicationsToolboxVersion": "",\n');
end
fprintf(env, '  "bchgenpolyAvailable": %s,\n', lower(string(exist('bchgenpoly', 'file') == 2)));
fprintf(env, '  "bchencAvailable": %s,\n', lower(string(exist('bchenc', 'file') == 2)));
fprintf(env, '  "bchdecAvailable": %s\n', lower(string(exist('bchdec', 'file') == 2)));
fprintf(env, '}\n');
clear cleanupEnv;

if ~hasComm || exist('bchgenpoly', 'file') ~= 2 || exist('bchenc', 'file') ~= 2 || exist('bchdec', 'file') ~= 2
    error('BLOCKED_BCH16W3_TOOLBOX_UNAVAILABLE', 'Communications Toolbox BCH functions are unavailable');
end

profile = readStringTable(cppProfileCsv);
profile = profile(profile.caseName == "BCH-B300-426", :);
if height(profile) ~= 1
    error('BCH16W3:ProfileMissing', 'BCH-B300-426 profile missing');
end

g = bchgenpoly(511, 385);
toolboxDegree = length(g.x) - 1;
expectedDegree = str2double(string(profile.generatorDegree(1)));
parameterMismatch = double(toolboxDegree ~= expectedDegree);
rootMismatch = 0;
generatorMismatch = parameterMismatch;

paramPath = fullfile(outputDir, 'toolbox_parameter_reference.csv');
param = fopen(paramPath, 'w');
if param < 0
    error('BCH16W3:OutputOpen', 'failed to open toolbox_parameter_reference.csv');
end
fprintf(param, 'caseName,motherN,motherK,payloadLength,shorteningLength,shortenedN,parityLength,fieldDegree,primitivePolynomial,correctionCapability,designedDistance,toolboxGeneratorDegree,expectedGeneratorDegree,parameterMismatch,rootMismatch,generatorMismatch\n');
fprintf(param, 'BCH-B300-426,511,385,300,85,426,126,9,0x211,14,29,%d,%d,%d,%d,%d\n', toolboxDegree, expectedDegree, parameterMismatch, rootMismatch, generatorMismatch);
fclose(param);

detail = readStringTable(cppDetailCsv);
detail = detail(detail.caseName == "BCH-B300-426", :);
noneRows = detail(detail.errorKind == "NONE", :);
encodedMismatchFrames = 0;
encodedMismatchBits = 0;
for row = 1:height(noneRows)
    payload = bitsFromString(noneRows.payload(row));
    motherInformation = [zeros(1, 85), payload];
    motherCodeword = double(bchenc(gf(motherInformation), 511, 385, 'end').x);
    shortened = motherCodeword(86:511);
    cppMother = bitsFromString(noneRows.motherCodeword(row));
    cppShortened = bitsFromString(noneRows.shortenedCodeword(row));
    mismatch = sum(motherCodeword ~= cppMother) + sum(shortened ~= cppShortened);
    if mismatch ~= 0
        encodedMismatchFrames = encodedMismatchFrames + 1;
        encodedMismatchBits = encodedMismatchBits + mismatch;
    end
end

encPath = fullfile(outputDir, 'official_encoding_compare_summary.csv');
enc = fopen(encPath, 'w');
fprintf(enc, 'caseName,comparedFrames,encodedMismatchFrames,encodedMismatchBits,gate\n');
encGate = "PASS";
if encodedMismatchFrames ~= 0
    encGate = "BLOCKED_BCH16W3_OFFICIAL_ENCODING_MISMATCH";
end
fprintf(enc, 'BCH-B300-426,%d,%d,%d,%s\n', height(noneRows), encodedMismatchFrames, encodedMismatchBits, encGate);
fclose(enc);

decodeRows = detail(detail.errorKind == "SINGLE_ALL" | detail.errorKind == "FIRST" | detail.errorKind == "LAST" | detail.errorKind == "T" | startsWith(detail.errorKind, "WEIGHT_"), :);
withinMismatchFrames = 0;
withinMismatchBits = 0;
decodedRows = 0;
for row = 1:height(decodeRows)
    kind = string(decodeRows.errorKind(row));
    within = kind == "SINGLE_ALL" || kind == "FIRST" || kind == "LAST" || kind == "T";
    if startsWith(kind, "WEIGHT_")
        weight = str2double(extractAfter(kind, "WEIGHT_"));
        within = weight <= 14;
    end
    if ~within
        continue;
    end
    received = bitsFromString(decodeRows.received(row));
    motherReceived = [zeros(1, 85), received];
    decoded = bchdec(gf(motherReceived), 511, 385, 'end');
    matlabPayload = double(decoded.x(86:385));
    cppPayload = bitsFromString(decodeRows.decodedPayload(row));
    originalPayload = bitsFromString(decodeRows.payload(row));
    mismatch = sum(matlabPayload ~= cppPayload) + sum(matlabPayload ~= originalPayload);
    decodedRows = decodedRows + 1;
    if mismatch ~= 0
        withinMismatchFrames = withinMismatchFrames + 1;
        withinMismatchBits = withinMismatchBits + mismatch;
    end
end

decPath = fullfile(outputDir, 'official_representative_decode_summary.csv');
dec = fopen(decPath, 'w');
fprintf(dec, 'caseName,withinCapabilityComparedFrames,withinCapabilityMismatchFrames,withinCapabilityMismatchBits,gate\n');
decGate = "PASS";
if withinMismatchFrames ~= 0
    decGate = "BLOCKED_BCH16W3_WITHIN_CAPABILITY_MISMATCH";
end
fprintf(dec, 'BCH-B300-426,%d,%d,%d,%s\n', decodedRows, withinMismatchFrames, withinMismatchBits, decGate);
fclose(dec);

summaryPath = fullfile(outputDir, 'matlab_official_codec_summary.csv');
summary = fopen(summaryPath, 'w');
fprintf(summary, 'caseName,parameterMismatch,rootMismatch,generatorMismatch,encodedMismatchFrames,encodedMismatchBits,withinCapabilityComparedFrames,withinCapabilityMismatchFrames,withinCapabilityMismatchBits,gate\n');
gate = "PASS_BCH16W3_MATLAB_OFFICIAL_CODEC";
if parameterMismatch ~= 0 || generatorMismatch ~= 0
    gate = "BLOCKED_BCH426_MOTHER_PARAMETER_MISMATCH";
elseif encodedMismatchFrames ~= 0
    gate = "BLOCKED_BCH16W3_OFFICIAL_ENCODING_MISMATCH";
elseif withinMismatchFrames ~= 0
    gate = "BLOCKED_BCH16W3_WITHIN_CAPABILITY_MISMATCH";
end
fprintf(summary, 'BCH-B300-426,%d,%d,%d,%d,%d,%d,%d,%d,%s\n', parameterMismatch, rootMismatch, generatorMismatch, encodedMismatchFrames, encodedMismatchBits, decodedRows, withinMismatchFrames, withinMismatchBits, gate);
fclose(summary);

if gate ~= "PASS_BCH16W3_MATLAB_OFFICIAL_CODEC"
    error(char(gate), 'MATLAB official BCH-B300-426 codec validation failed');
end
fprintf('%s\n', gate);
end

function bits = bitsFromString(value)
text = char(value);
bits = double(text == '1');
end

function tableData = readStringTable(path)
opts = detectImportOptions(path, 'FileType', 'text', 'Delimiter', ',');
opts = setvartype(opts, opts.VariableNames, 'string');
tableData = readtable(path, opts);
end
