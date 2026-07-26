function run_bch_s2_batch2_reference(inputCsv, outputCsv)
% Independent MATLAB channel/reference implementation for BCH S2-05..S2-07.
addpath(fullfile(fileparts(mfilename('fullpath')), '..', '..', '..', 'segmented', 'matlab'));
opts = detectImportOptions(inputCsv, 'Delimiter', ',', 'VariableNamingRule', 'preserve');
opts = setvartype(opts, opts.VariableNames, 'string');
data = readtable(inputCsv, opts);
numeric = ["parameterPoint","payloadLength","encodedLength","frameRate", ...
    "sourcePayloadEbN0Db","snrDb","frameIndex","initialPhaseDeg", ...
    "frameRotationDeg","attenuationDb","completeBlockage","startIndex", ...
    "impairmentLength","cppReportedSuccess","cppTrueSuccess", ...
    "cppMiscorrection","cppDecoderFailure"];
for name = numeric
    data.(name) = str2double(data.(name));
end
if height(data) ~= 4500
    error('BLOCKED_BCH_S2_09_INPUT_INCOMPLETE', 'expected 4500 rows');
end
cases = ["BCH-S200","BCH-B200","BCH-S300","BCH-B300","BCH-B300-426"];
channels = ["RESIDUAL_CFO","SHORT_BLOCKAGE","BURST"];
lookup = bch15_build_lookup_reference();
summary = table('Size',[45 14], ...
    'VariableTypes', ["string","double","string","double","double","double", ...
        "double","double","double","double","double","double","double","string"], ...
    'VariableNames', ["channelType","parameterPoint","caseName","comparedFrames", ...
        "maxSampleAbsDiff","hardBitMismatches","decodedPayloadBitMismatches", ...
        "frameErrorMismatches","reportedStatusMismatches","miscorrectionMismatches", ...
        "decoderFailureMismatches","matlabFrameErrors","cppFrameErrors","gate"]);
outRow = 0;
for channel = channels
    for point = 0:2
        for caseName = cases
            selected = data(data.channelType == channel & ...
                data.parameterPoint == point & data.caseName == caseName,:);
            if height(selected) ~= 100
                error('BLOCKED_BCH_S2_09_INPUT_INCOMPLETE', 'missing representative frames');
            end
            sampleDiff = 0; hardMismatch = 0; payloadMismatch = 0;
            frameMismatch = 0; reportedMismatch = 0; miscorrectionMismatch = 0;
            failureMismatch = 0; matlabFE = 0; cppFE = 0;
            for row = 1:height(selected)
                original = bitsFromString(selected.payloadBits(row));
                encoded = bitsFromString(selected.encodedBits(row));
                noise = doublesFromString(selected.standardNoise(row));
                cppReal = doublesFromString(selected.cppSampleReal(row));
                cppImag = doublesFromString(selected.cppSampleImag(row));
                cppHard = bitsFromString(selected.cppHardBits(row));
                cppPayload = bitsFromString(selected.cppDecodedPayload(row));
                x = 1 - 2 * encoded;
                snr = selected.snrDb(row);
                realVariance = 1 / (2 * 10^(snr / 10));
                if channel == "RESIDUAL_CFO"
                    n = numel(x);
                    delta = deg2rad(selected.frameRotationDeg(row)) / (n - 1);
                    phase = deg2rad(selected.initialPhaseDeg(row)) + (0:n-1) * delta;
                    z = noise(1:2:end) + 1i * noise(2:2:end);
                    received = x .* exp(1i * phase) + sqrt(realVariance) * z;
                    if selected.compensationMode(row) == "PERFECT"
                        samples = received .* exp(-1i * phase);
                    else
                        samples = received;
                    end
                    hard = double(real(samples) < 0);
                elseif channel == "SHORT_BLOCKAGE"
                    amplitude = 10^(selected.attenuationDb(row) / 20);
                    if selected.completeBlockage(row) ~= 0
                        amplitude = 0;
                    end
                    mask = ones(size(x));
                    first = selected.startIndex(row) + 1;
                    last = first + selected.impairmentLength(row) - 1;
                    mask(first:last) = amplitude;
                    samples = mask .* x + sqrt(realVariance) * noise;
                    hard = double(samples < 0);
                else
                    if selected.burstMode(row) == "PURE"
                        samples = x;
                    else
                        samples = x + sqrt(realVariance) * noise;
                    end
                    hard = double(samples < 0);
                    first = selected.startIndex(row) + 1;
                    last = first + selected.impairmentLength(row) - 1;
                    hard(first:last) = 1 - hard(first:last);
                end
                cppSamples = cppReal + 1i * cppImag;
                sampleDiff = max(sampleDiff, max(abs(samples - cppSamples)));
                hardMismatch = hardMismatch + sum(hard ~= cppHard);
                [matlabPayload, reported] = decodeWithStatus(caseName, hard, lookup);
                payloadMismatch = payloadMismatch + sum(matlabPayload ~= cppPayload);
                trueSuccess = all(matlabPayload == original);
                frameError = ~trueSuccess;
                miscorrection = reported && frameError;
                failure = ~reported;
                cppFrameError = ~logical(selected.cppTrueSuccess(row));
                frameMismatch = frameMismatch + (frameError ~= cppFrameError);
                reportedMismatch = reportedMismatch + ...
                    (reported ~= logical(selected.cppReportedSuccess(row)));
                miscorrectionMismatch = miscorrectionMismatch + ...
                    (miscorrection ~= logical(selected.cppMiscorrection(row)));
                failureMismatch = failureMismatch + ...
                    (failure ~= logical(selected.cppDecoderFailure(row)));
                matlabFE = matlabFE + frameError;
                cppFE = cppFE + cppFrameError;
            end
            gate = "PASS";
            if sampleDiff > 1e-12 || hardMismatch ~= 0 || payloadMismatch ~= 0 || ...
                    frameMismatch ~= 0 || reportedMismatch ~= 0 || ...
                    miscorrectionMismatch ~= 0 || failureMismatch ~= 0
                gate = "BLOCKED_BCH_S2_09_MATLAB_MISMATCH";
            end
            outRow = outRow + 1;
            summary(outRow,:) = {channel,point,caseName,height(selected),sampleDiff, ...
                hardMismatch,payloadMismatch,frameMismatch,reportedMismatch, ...
                miscorrectionMismatch,failureMismatch,matlabFE,cppFE,gate};
        end
    end
end
writetable(summary, outputCsv);
if any(summary.gate ~= "PASS")
    error('BLOCKED_BCH_S2_09_MATLAB_MISMATCH', 'independent reference mismatch');
end
fprintf('PASS_BCH_S2_09_MATLAB_CHANNEL_REFERENCE rows=%d frames=%d\n', ...
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
