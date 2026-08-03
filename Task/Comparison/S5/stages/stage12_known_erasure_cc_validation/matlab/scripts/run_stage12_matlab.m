function run_stage12_matlab(stageDir)
% Stage12 independent MATLAB official convolutional-code validation.
% Only the fixed-vector payload is shared with C++; all encoding, puncturing,
% channel metrics and decoding are independently generated here.

if nargin ~= 1
    error('stageDir is required');
end
stageDir = char(stageDir);
resultDir = fullfile(stageDir, 'matlab', 'results');
traceDir = fullfile(stageDir, 'matlab', 'traces');
if ~exist(resultDir, 'dir'), mkdir(resultDir); end
if ~exist(traceDir, 'dir'), mkdir(traceDir); end

trellis = poly2trellis(7, [171 133]);
puncture = [1; 1; 0; 1];

% Shared-payload fixed-vector audit; MATLAB independently encodes/decodes.
fixedPayloadTable = readtable(fullfile(stageDir, 'cpp', 'results', 'fixed_payload.csv'));
fixedPayload = double(fixedPayloadTable.payloadBit).';
fixedInput = [fixedPayload zeros(1, 6)];
fixedMother = convenc(fixedInput, trellis);
keep = repmat([1 1 0 1], 1, ceil(numel(fixedMother) / 4));
fixedTx = fixedMother(logical(keep(1:numel(fixedMother))));
fixedDecoded = vitdec(1 - 2 * fixedTx, trellis, 306, 'term', 'unquant', puncture);
assert(numel(fixedMother) == 612);
assert(numel(fixedTx) == 459);
assert(isequal(fixedDecoded(1:300), fixedPayload));
write_bits(fullfile(resultDir, 'fixed_matlab_mother_code_bits.csv'), 'motherBit', fixedMother);
write_bits(fullfile(resultDir, 'fixed_matlab_punctured_tx_bits.csv'), 'txBit', fixedTx);
write_bits(fullfile(resultDir, 'fixed_matlab_noiseless_decoded_payload.csv'), 'decodedBit', fixedDecoded(1:300));

outPath = fullfile(resultDir, 'matlab_independent_erasure_summary.csv');
out = fopen(outPath, 'w');
assert(out >= 0);
cleaner = onCleanup(@() fclose(out));
fprintf(out, ['scheme,erasureFraction,esN0Db,processedFrames,payloadBitErrors,frameErrors,' ...
    'BER,FER,ferWilsonLow,ferWilsonHigh,stopReason,payloadSeed,awgnSeed\n']);

fractions = [0 0.05];
snrs = [0 4 8 10];
for fraction = fractions
    for snr = snrs
        payloadSeed = 2026080311 + round(100 * fraction) * 100 + round(snr + 10);
        awgnSeed = 2026081312 + round(100 * fraction) * 100 + round(snr + 10);
        eraseSeed = 2026082313 + round(100 * fraction) * 100 + round(snr + 10);
        payloadStream = RandStream('mt19937ar', 'Seed', payloadSeed);
        awgnStream = RandStream('mt19937ar', 'Seed', awgnSeed);
        eraseStream = RandStream('mt19937ar', 'Seed', eraseSeed);
        frames = 0; bitErrors = 0; frameErrors = 0;
        sigmaSquared = 1 / (2 * 10^(snr / 10));
        sigma = sqrt(sigmaSquared);
        while frames < 10000
            payload = randi(payloadStream, [0 1], 1, 300);
            mother = convenc([payload zeros(1, 6)], trellis);
            keep = repmat([1 1 0 1], 1, ceil(numel(mother) / 4));
            tx = mother(logical(keep(1:numel(mother))));
            assert(numel(tx) == 459);
            symbols = 1 - 2 * tx;
            erasureLength = round(fraction * numel(tx));
            if erasureLength > 0
                erasureStart = randi(eraseStream, [1 numel(tx) - erasureLength + 1]);
                erased = erasureStart:(erasureStart + erasureLength - 1);
                symbols(erased) = 0;
            else
                erased = [];
            end
            received = symbols + sigma * randn(awgnStream, 1, numel(tx));
            llr = 2 * received / sigmaSquared;
            llr(erased) = 0;
            decoded = vitdec(llr / 2, trellis, 306, 'term', 'unquant', puncture);
            currentErrors = sum(decoded(1:300) ~= payload);
            frames = frames + 1;
            bitErrors = bitErrors + currentErrors;
            frameErrors = frameErrors + (currentErrors > 0);
            if frames >= 1000 && frameErrors >= 200
                break;
            end
        end
        [low, high] = wilson(frameErrors, frames);
        if frameErrors >= 200, stopReason = 'TARGET_FRAME_ERRORS'; else, stopReason = 'MAX_FRAMES'; end
        fprintf(out, 'CC_R23,%.17g,%.17g,%d,%d,%d,%.17g,%.17g,%.17g,%.17g,%s,%d,%d\n', ...
            fraction, snr, frames, bitErrors, frameErrors, bitErrors/(300*frames), ...
            frameErrors/frames, low, high, stopReason, payloadSeed, awgnSeed);
        fprintf('MATLAB Stage12 fraction=%.2f snr=%.1f frames=%d FE=%d\n', fraction, snr, frames, frameErrors);
    end
end

report = fopen(fullfile(resultDir, 'matlab_official_cc_validation.md'), 'w');
assert(report >= 0);
fprintf(report, '# MATLAB官方卷积码独立验证\n\n');
fprintf(report, '- MATLAB版本：%s\n', version);
fprintf(report, '- 官方函数：poly2trellis、convenc、vitdec\n');
fprintf(report, '- 固定向量：仅共享原始payload；MATLAB独立编码、打孔和译码。\n');
fprintf(report, '- 统计验证：独立payload seed、AWGN seed和擦除位置seed。\n');
fprintf(report, '- 母码长度：612；R2/3发送长度：459；打孔模式：[1 1 0 1]。\n');
fprintf(report, '- 固定向量无噪声译码：PASS。\n');
fclose(report);
disp('PASS_STAGE12_MATLAB_EXECUTION');
end

function write_bits(path, name, bits)
out = fopen(path, 'w'); assert(out >= 0);
fprintf(out, 'index,%s\n', name);
for k = 1:numel(bits), fprintf(out, '%d,%d\n', k-1, bits(k)); end
fclose(out);
end

function [low, high] = wilson(errors, n)
z = 1.959963984540054;
p = errors / n;
den = 1 + z^2 / n;
center = (p + z^2/(2*n)) / den;
half = z * sqrt((p*(1-p) + z^2/(4*n))/n) / den;
low = center - half;
high = center + half;
end
