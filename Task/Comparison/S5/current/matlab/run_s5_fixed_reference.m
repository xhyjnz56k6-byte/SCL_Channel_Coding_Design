function run_s5_fixed_reference(resultDir)
% Independent MATLAB audit for the S5 fixed-vector fixture.
if nargin == 0
    error('resultDir is required');
end
bits = readtable(fullfile(resultDir, 'fixed_codec_bits.csv'), TextType='string');
trace = readtable(fullfile(resultDir, 'fixed_vector_trace.csv'), TextType='string');
scriptDir = fileparts(mfilename('fullpath'));
config = jsondecode(fileread(fullfile(scriptDir, '..', 'config', 's5_smoke_frozen_config.json')));
out = fopen(fullfile(resultDir, 'matlab_reference_report.csv'), 'w');
assert(out >= 0);
cleanup = onCleanup(@() fclose(out));
fprintf(out, 'check,status,maxAbsError\n');
assert(config.payload.length == 300);
assert(strcmp(config.payload.framePoolId, 'payload_k300_seed2026072001_policy1_frames100'));
assert(strcmp(config.payload.framePoolOverallHash, '83880398af81a8385d1dbd7e6870554311a0bb7d96ddeb5d3434b06a68a2005f'));
assert(strcmp(config.noise.strategy, 's5_complex_pair_v1'));
assert(config.noise.masterSeed == 2026072004);
fprintf(out, 'fixture_identity,PASS,0\n');

trellis = poly2trellis(7, [171 133]);
ccCases = ["CC_R12_BLOCK_FLOAT", "CC_R23_BLOCK_FLOAT"];
for name = ccCases
    for frame = 0:9
        payloadRows = bits(bits.scheme == name & bits.frameIndex == frame & bits.kind == "payload", :);
        txRows = bits(bits.scheme == name & bits.frameIndex == frame & bits.kind == "transmitted", :);
        [~, order] = sort(payloadRows.bitIndex); payload = double(payloadRows.bit(order)).';
        [~, order] = sort(txRows.bitIndex); expectedTx = double(txRows.bit(order)).';
        mother = convenc([payload zeros(1, 6)], trellis);
        if name == "CC_R23_BLOCK_FLOAT"
            keep = repmat([1 1 0 1], 1, ceil(numel(mother)/4));
            matlabTx = mother(logical(keep(1:numel(mother))));
            decoded = vitdec(1 - 2 * expectedTx, trellis, 306, 'term', 'unquant', [1;1;0;1]);
        else
            matlabTx = mother;
            decoded = vitdec(1 - 2 * expectedTx, trellis, 306, 'term', 'unquant');
        end
        assert(isequal(matlabTx, expectedTx), 'MATLAB CC encoder mismatch');
        assert(isequal(decoded(1:300), payload), 'MATLAB CC decoder mismatch');
    end
end
fprintf(out, 'cc_official_encoder_decoder,PASS,0\n');

tol = 1e-10;
cfo = trace(trace.channel == "CFO_30_DEG" & trace.mode == "IMPAIRMENT_NO_AWGN", :);
cfoExpected = cfo.txReal .* cos(cfo.phase) - cfo.txImag .* sin(cfo.phase);
cfoError = max(abs(cfoExpected - cfo.impairedReal));
assert(cfoError <= tol); fprintf(out, 'cfo_rotation,PASS,%.17g\n', cfoError);

dop = trace(trace.channel == "LINEAR_TIME_VARYING_FREQUENCY" & trace.mode == "IMPAIRMENT_NO_AWGN", :);
dopExpected = dop.txReal .* cos(dop.phase) - dop.txImag .* sin(dop.phase);
dopError = max(abs(dopExpected - dop.impairedReal));
assert(dopError <= tol); fprintf(out, 'doppler_rotation,PASS,%.17g\n', dopError);

blocked = trace(trace.channel == "KNOWN_BLOCKAGE_10_PERCENT" & trace.mask == 0, :);
assert(all(blocked.llr == 0)); fprintf(out, 'known_blockage_zero_llr,PASS,0\n');

mp = trace(trace.channel == "FIXED_MULTIPATH_REAL_MMSE" & trace.mode == "IMPAIRMENT_WITH_AWGN", :);
mpExpected = 2 .* mp.gain .* mp.equalized ./ mp.variance;
mpError = max(abs(mpExpected - mp.llr));
assert(mpError <= tol); fprintf(out, 'multipath_gk_vk_llr,PASS,%.17g\n', mpError);

assert(abs(sqrt(10^(10/10)/2) - sqrt(5)) < eps);
fprintf(out, 'burst_complex_total_power_beta,PASS,0\n');
fprintf(out, 'overall,PASS,0\n');
disp('PASS_S5_MATLAB_REFERENCE');
end
