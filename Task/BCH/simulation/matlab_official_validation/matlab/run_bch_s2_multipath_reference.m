function run_bch_s2_multipath_reference(inputCsv, outputCsv)
% Independent MATLAB reference for the frozen S2 channel, MMSE and BCH payload result.
addpath(fullfile(fileparts(mfilename('fullpath')), '..', '..', '..', 'segmented', 'matlab'));
opts = detectImportOptions(inputCsv, 'Delimiter', ',', 'VariableNamingRule', 'preserve');
opts = setvartype(opts, opts.VariableNames, 'string');
data = readtable(inputCsv, opts);
data.payloadLength = str2double(data.payloadLength);
data.encodedLength = str2double(data.encodedLength);
data.sourcePayloadEbN0Db = str2double(data.sourcePayloadEbN0Db);
data.snrDb = str2double(data.snrDb);
data.noiseVariance = str2double(data.noiseVariance);
data.frameIndex = str2double(data.frameIndex);
data.cppDecodedFrameError = str2double(data.cppDecodedFrameError);
requiredCases = ["BCH-S200","BCH-B200","BCH-S300","BCH-B300","BCH-B300-426"];
if height(data) ~= 1500 || ~all(ismember(requiredCases, unique(data.caseName)))
    error('BLOCKED_BCH_S2_MATLAB_INPUT_INCOMPLETE', 'expected 1500 rows and five cases');
end
h = [1.0; 0.65; 0.35] / sqrt(1.545);
delays = [0; 1; 3];
lookup = bch15_build_lookup_reference();
summary = table('Size',[15 13], ...
    'VariableTypes', ["string","double","double","double","double","double","double","double","double","double","double","double","string"], ...
    'VariableNames', ["caseName","sourcePayloadEbN0Db","comparedFrames","normalizedTapMaxAbsDiff", ...
    "fullConvolutionMaxAbsDiff","receivedMaxAbsDiff","equalizedMaxAbsDiff","hardBitMismatches", ...
    "decodedPayloadBitMismatches","decodedFrameErrorMismatches","matlabDecodedFrameErrors", ...
    "cppDecodedFrameErrors","gate"]);
outRow = 0;
for c = 1:numel(requiredCases)
    caseName = requiredCases(c);
    for ebn0 = [8, 10, 14]
        selected = data(data.caseName == caseName & abs(data.sourcePayloadEbN0Db-ebn0)<1e-12,:);
        maxConv = 0; maxRx = 0; maxEq = 0; hardMismatch = 0;
        payloadMismatch = 0; frameMismatch = 0; matlabFE = 0; cppFE = 0;
        n = selected.encodedLength(1);
        H = zeros(n+3,n);
        for column = 1:n
            for tap = 1:numel(h)
                H(column+delays(tap),column) = h(tap);
            end
        end
        variance = selected.noiseVariance(1);
        normal = H' * H + variance * eye(n);
        for row = 1:height(selected)
            encoded = bitsFromString(selected.encodedBits(row));
            z = doublesFromString(selected.standardNoise(row));
            cppConv = doublesFromString(selected.cppFullConvolution(row));
            cppRx = doublesFromString(selected.cppReceivedSamples(row));
            cppEq = doublesFromString(selected.cppEqualizedSymbols(row));
            cppHard = bitsFromString(selected.cppHardBits(row));
            cppPayload = bitsFromString(selected.cppDecodedPayload(row));
            original = bitsFromString(selected.payloadBits(row));
            x = 1 - 2 * encoded(:);
            convolution = H * x;
            received = convolution + sqrt(variance) * z(:);
            equalized = normal \ (H' * received);
            hard = double(equalized < 0).';
            maxConv = max(maxConv, max(abs(convolution - cppConv(:))));
            maxRx = max(maxRx, max(abs(received - cppRx(:))));
            maxEq = max(maxEq, max(abs(equalized - cppEq(:))));
            hardMismatch = hardMismatch + sum(hard ~= cppHard);
            matlabPayload = decodePayload(caseName, hard, lookup);
            payloadMismatch = payloadMismatch + sum(matlabPayload ~= cppPayload);
            matlabError = any(matlabPayload ~= original);
            cppError = logical(selected.cppDecodedFrameError(row));
            frameMismatch = frameMismatch + (matlabError ~= cppError);
            matlabFE = matlabFE + matlabError;
            cppFE = cppFE + cppError;
        end
        outRow = outRow + 1;
        gate = "PASS";
        if hardMismatch ~= 0 || payloadMismatch ~= 0 || frameMismatch ~= 0 || maxEq > 1e-10
            gate = "BLOCKED_BCH_S2_04_MATLAB_HARD_DECISION_MISMATCH";
        end
        summary(outRow,:) = {caseName,ebn0,height(selected),max(abs(h-[1;0.65;0.35]/sqrt(1.545))), ...
            maxConv,maxRx,maxEq,hardMismatch,payloadMismatch,frameMismatch,matlabFE,cppFE,gate};
    end
end
writetable(summary, outputCsv);
if any(summary.gate ~= "PASS")
    error('BLOCKED_BCH_S2_04_MATLAB_HARD_DECISION_MISMATCH', 'MATLAB reference mismatch');
end
fprintf('PASS_BCH_S2_04_MATLAB_REFERENCE rows=%d\n', height(summary));
end

function values = doublesFromString(text)
values = str2double(split(string(text), ';')).';
end

function values = bitsFromString(text)
values = double(char(text) == '1');
end

function payload = decodePayload(caseName, hard, lookup)
if caseName == "BCH-S200" || caseName == "BCH-S300"
    decoded = bch15_segmented_decode_reference(char(caseName), hard, lookup);
    payload = decoded.recoveredPayload;
    return;
end
if caseName == "BCH-B200"
    n=255; k=207; shortening=7;
elseif caseName == "BCH-B300"
    n=511; k=421; shortening=121;
else
    n=511; k=385; shortening=85;
end
motherReceived = [zeros(1,shortening), hard];
decoded = bchdec(gf(motherReceived), n, k, 'end');
payload = double(decoded.x(shortening+1:k));
end
