function run_bch_s2_corrected_cfo_reference(inputCsv, outputCsv)
% Independent MATLAB validation for corrected residual-CFO semantics.
addpath(fullfile(fileparts(mfilename('fullpath')), '..', '..', '..', 'segmented', 'matlab'));
opts = detectImportOptions(inputCsv, 'Delimiter', ',', 'VariableNamingRule', 'preserve');
opts = setvartype(opts, opts.VariableNames, 'string');
data = readtable(inputCsv, opts);
numeric = ["payloadLength","encodedLength","frameRate","frameIndex", ...
    "sourcePayloadEbN0Db","snrDb","initialPhaseDeg","frameRotationDeg", ...
    "cppNoCompTrueSuccess","cppPerfectTrueSuccess"];
for name = numeric
    data.(name) = str2double(data.(name));
end
if height(data) ~= 3500
    error('BLOCKED_BCH_S2_CORRECTED_MATLAB_INPUT', 'expected 3500 rows');
end
cases = ["BCH-S200","BCH-B200","BCH-S300","BCH-B300","BCH-B300-426"];
classes = ["RESIDUAL_CFO_PHI0_ZERO","INITIAL_PHASE_SENSITIVITY"];
lookup = bch15_build_lookup_reference();
summary = table('Size',[35 14], ...
    'VariableTypes', ["string","string","double","double","double","double", ...
        "double","double","double","double","double","double","double","string"], ...
    'VariableNames', ["experimentClass","caseName","initialPhaseDeg", ...
        "frameRotationDeg","comparedFrames","maxReceivedAbsDiff", ...
        "maxPerfectCompensatedAbsDiff","maxPerfectAwgnRealAbsDiff", ...
        "noCompHardBitMismatches","perfectHardBitMismatches", ...
        "noCompDecodedPayloadBitMismatches", ...
        "perfectDecodedPayloadBitMismatches","frameErrorMismatches","gate"]);
outRow = 0;
for className = classes
    for caseName = cases
        classRows = data(data.experimentClass == className & data.caseName == caseName,:);
        if className == "RESIDUAL_CFO_PHI0_ZERO"
            parameters = [0 30 60];
            parameterField = "frameRotationDeg";
        else
            parameters = [0 45 90 135];
            parameterField = "initialPhaseDeg";
        end
        for parameter = parameters
            selected = classRows(classRows.(parameterField) == parameter,:);
            if height(selected) ~= 100
                error('BLOCKED_BCH_S2_CORRECTED_MATLAB_INPUT', 'missing frames');
            end
            receivedDiff = 0; perfectDiff = 0; awgnDiff = 0;
            noHardMismatch = 0; perfectHardMismatch = 0;
            noPayloadMismatch = 0; perfectPayloadMismatch = 0;
            frameMismatch = 0;
            for row = 1:height(selected)
                original = bitsFromString(selected.payloadBits(row));
                encoded = bitsFromString(selected.encodedBits(row));
                noise = doublesFromString(selected.standardComplexNoise(row));
                cppReceived = doublesFromString(selected.cppReceivedReal(row)) + ...
                    1i * doublesFromString(selected.cppReceivedImag(row));
                cppPerfect = doublesFromString(selected.cppPerfectReal(row)) + ...
                    1i * doublesFromString(selected.cppPerfectImag(row));
                x = 1 - 2 * encoded;
                realVariance = 1 / (2 * 10^(selected.snrDb(row) / 10));
                baseband = x + sqrt(realVariance) * ...
                    (noise(1:2:end) + 1i * noise(2:2:end));
                n = numel(x);
                delta = deg2rad(selected.frameRotationDeg(row)) / (n - 1);
                phase = deg2rad(selected.initialPhaseDeg(row)) + (0:n-1) * delta;
                received = baseband .* exp(1i * phase);
                perfect = received .* exp(-1i * phase);
                noHard = double(real(received) < 0);
                perfectHard = double(real(perfect) < 0);
                cppNoHard = bitsFromString(selected.cppNoCompHardBits(row));
                cppPerfectHard = bitsFromString(selected.cppPerfectHardBits(row));
                receivedDiff = max(receivedDiff, max(abs(received - cppReceived)));
                perfectDiff = max(perfectDiff, max(abs(perfect - cppPerfect)));
                awgnDiff = max(awgnDiff, max(abs(real(perfect) - ...
                    (x + sqrt(realVariance) * noise(1:2:end)))));
                noHardMismatch = noHardMismatch + sum(noHard ~= cppNoHard);
                perfectHardMismatch = perfectHardMismatch + ...
                    sum(perfectHard ~= cppPerfectHard);
                [noPayload, ~] = decodeWithStatus(caseName, noHard, lookup);
                [perfectPayload, ~] = decodeWithStatus(caseName, perfectHard, lookup);
                cppNoPayload = bitsFromString(selected.cppNoCompDecodedPayload(row));
                cppPerfectPayload = bitsFromString( ...
                    selected.cppPerfectDecodedPayload(row));
                noPayloadMismatch = noPayloadMismatch + ...
                    sum(noPayload ~= cppNoPayload);
                perfectPayloadMismatch = perfectPayloadMismatch + ...
                    sum(perfectPayload ~= cppPerfectPayload);
                noError = ~all(noPayload == original);
                perfectError = ~all(perfectPayload == original);
                frameMismatch = frameMismatch + ...
                    (noError ~= ~logical(selected.cppNoCompTrueSuccess(row))) + ...
                    (perfectError ~= ~logical(selected.cppPerfectTrueSuccess(row)));
            end
            gate = "PASS";
            if receivedDiff > 1e-12 || perfectDiff > 1e-12 || ...
                    awgnDiff > 1e-12 || noHardMismatch ~= 0 || ...
                    perfectHardMismatch ~= 0 || noPayloadMismatch ~= 0 || ...
                    perfectPayloadMismatch ~= 0 || frameMismatch ~= 0
                gate = "BLOCKED_BCH_S2_CORRECTED_MATLAB_MISMATCH";
            end
            outRow = outRow + 1;
            summary(outRow,:) = {className,caseName, ...
                selected.initialPhaseDeg(1),selected.frameRotationDeg(1), ...
                height(selected),receivedDiff,perfectDiff,awgnDiff, ...
                noHardMismatch,perfectHardMismatch,noPayloadMismatch, ...
                perfectPayloadMismatch,frameMismatch,gate};
        end
    end
end
writetable(summary, outputCsv);
if any(summary.gate ~= "PASS")
    error('BLOCKED_BCH_S2_CORRECTED_MATLAB_MISMATCH', 'reference mismatch');
end
fprintf('PASS_BCH_S2_CORRECTED_MATLAB_REFERENCE rows=%d frames=%d\n', ...
    height(summary), sum(summary.comparedFrames));
end

function values = doublesFromString(text)
values = str2double(split(string(text), ';')).';
end

function values = bitsFromString(text)
values = double(char(text) == '1');
end

function [payload, reported] = decodeWithStatus(caseName, hard, lookup)
if caseName == "BCH-S200" || caseName == "BCH-S300"
    decoded = bch15_segmented_decode_reference(char(caseName), hard, lookup);
    payload = decoded.recoveredPayload;
    reported = decoded.frameDetail.lookupMissBlocks == 0 && ...
        decoded.frameDetail.postCheckFailedBlocks == 0;
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
[decoded, errors] = bchdec(gf(motherReceived), n, k, 'end');
payload = double(decoded.x(shortening+1:k));
reported = errors >= 0;
end
