function run_s7_smoke_reference(outputDir)
outputDir = char(java.io.File(outputDir).getCanonicalPath());
scriptDir = fileparts(mfilename('fullpath'));
repoRoot = char(java.io.File(fullfile(scriptDir, '..', '..', '..', '..', '..')).getCanonicalPath());
addpath(fullfile(repoRoot, 'Task', 'BCH', 'segmented', 'matlab'));

rows = strings(0,1); status = strings(0,1); detail = strings(0,1);
    function record(name, ok, message)
        rows(end+1,1) = string(name); %#ok<AGROW>
        status(end+1,1) = string(ternary(ok, 'PASS', 'FAIL')); %#ok<AGROW>
        detail(end+1,1) = string(message); %#ok<AGROW>
    end

mappingPath = fullfile(outputDir, 'mapping_vectors.csv');
m = readtable(mappingPath, 'TextType', 'string', 'VariableNamingRule', 'preserve');
keys = unique(m(:, {'scheme','method','parameter'}), 'rows', 'stable');
for k = 1:height(keys)
    mask = m.scheme == keys.scheme(k) & m.method == keys.method(k) & m.parameter == keys.parameter(k);
    actual = uint64(m.input_index(mask))';
    expected = expected_mapping(keys.scheme(k), keys.method(k), keys.parameter(k));
    record("mapping_" + keys.scheme(k) + "_" + keys.method(k) + "_" + keys.parameter(k), ...
        isequal(actual, expected), "indices");
    expectedHash = mapping_sha256(expected);
    record("mapping_hash_" + keys.scheme(k) + "_" + keys.method(k) + "_" + keys.parameter(k), ...
        all(m.mapping_sha256(mask) == expectedHash), expectedHash);
    record("mapping_permutation_" + k, numel(unique(actual)) == numel(actual) && ...
        min(actual) == 0 && max(actual) == numel(actual)-1, "unique/range");
    if keys.scheme(k) == "CC"
        record("cc_pair_" + keys.method(k) + "_" + keys.parameter(k), ...
            all(mod(actual(1:2:end),2)==0) && all(actual(2:2:end)==actual(1:2:end)+1), "mother pair");
    end
end

channelPath = fullfile(outputDir, 'channel_vector.csv');
c = readtable(channelPath, 'VariableNamingRule', 'preserve');
variance = 1/(2*10^(2/10));
expectedRx = (1-2*c.burst_mask).*c.bpsk + sqrt(variance).*c.standard_noise;
expectedHard = expectedRx < 0;
expectedLlr = 2*expectedRx/variance;
record('channel_received', max(abs(expectedRx-c.received)) < 2e-14, "max abs");
record('channel_hard', all(expectedHard==c.hard_bit), "hard bits");
record('channel_llr', max(abs(expectedLlr-c.llr)) < 5e-13, "max abs");

bchPath = fullfile(outputDir, 'bch_codec_vector.csv');
opts = detectImportOptions(bchPath, 'TextType', 'string');
opts = setvartype(opts, {'payload_bits','padded_message_bits','encoded_bits','decoded_payload_bits'}, 'string');
b = readtable(bchPath, opts);
payload = double(char(b.payload_bits(1))) - double('0');
reference = bch15_segmented_encode_reference('BCH-S200', payload);
record('bch_padded_bits', isequal(reference.paddedMessageBits, double(char(b.padded_message_bits(1)))-double('0')), "padded");
record('bch_encoded_bits', isequal(reference.encodedBits, double(char(b.encoded_bits(1)))-double('0')), "encoded");
record('bch_decoded_payload', b.payload_bits(1)==b.decoded_payload_bits(1), "payload");

syndromePath = fullfile(outputDir, 'bch_syndrome_vector.csv');
s = readtable(syndromePath);
syndromeOk = true;
for i = 1:height(s)
    error = zeros(1,15); error(s.error_position(i)+1)=1;
    value = bch15_syndrome_value(bch15_syndrome_reference(error));
    syndromeOk = syndromeOk && value==s.syndrome(i) && s.lookup_position(i)==s.error_position(i);
end
record('bch_syndrome_lookup', syndromeOk, "15 single-bit patterns");

trellisPath = fullfile(outputDir, 'cc_trellis_vector.csv');
t = readtable(trellisPath);
trellis = poly2trellis(7,[171 133]);
nextOk = true; outputOk = true;
for i=1:height(t)
    nextOk = nextOk && trellis.nextStates(t.state(i)+1,t.input_bit(i)+1)==t.next_state(i);
    outputOk = outputOk && trellis.outputs(t.state(i)+1,t.input_bit(i)+1)==t.output_decimal(i);
end
record('cc_state_numbering', nextOk, "states 0..63");
record('cc_generator_output_order', outputOk, "171 then 133");

ccPath = fullfile(outputDir, 'cc_codec_vector.csv');
opts = detectImportOptions(ccPath, 'TextType', 'string');
opts = setvartype(opts, {'payload_bits','codec_input_bits','mother_bits','decoded_payload_bits'}, 'string');
v = readtable(ccPath, opts);
codec = double(char(v.codec_input_bits(1)))-double('0');
mother = double(char(v.mother_bits(1)))-double('0');
[matlabMother, finalState] = convenc(codec, trellis);
record('cc_encoded_bits', isequal(matlabMother,mother) && finalState==v.final_state(1), "convenc");
[decoded, ties] = explicit_viterbi(1-2*mother, trellis, 306, 0, 0);
record('cc_noiseless_payload', isequal(decoded(1:300), double(char(v.decoded_payload_bits(1)))-double('0')), "explicit Viterbi");
[tieDecoded, tieCount] = explicit_viterbi(zeros(1,612), trellis, 306, 0, 0);
record('cc_tie_break_payload', isequal(tieDecoded(1:300), double(char(v.decoded_payload_bits(2)))-double('0')), "lower predecessor then input 0");
record('cc_tie_count', tieCount==v.tie_count(2) && ties==v.tie_count(1), "exact ties");
record('cc_traceback_final_state', all(v.traceback_final_state==0), "terminated state 0");

comparison = table(rows,status,detail,'VariableNames',{'check','status','detail'});
writetable(comparison, fullfile(outputDir,'matlab_comparison.csv'));
validation = struct('status',ternary(all(status=="PASS"),'PASS','FAIL'), ...
    'checkCount',height(comparison),'failedCount',sum(status~="PASS"), ...
    'mappingCsvAbsolutePath',char(java.io.File(mappingPath).getCanonicalPath()), ...
    'channelCsvAbsolutePath',char(java.io.File(channelPath).getCanonicalPath()));
fid=fopen(fullfile(outputDir,'matlab_validation.json'),'w'); fprintf(fid,'%s\n',jsonencode(validation,'PrettyPrint',true)); fclose(fid);
if any(status~="PASS"), error('S7 C++/MATLAB Smoke mismatch'); end
disp('PASS_S7_CPP_MATLAB_SMOKE');
end

function result = expected_mapping(scheme, method, parameter)
if scheme=="BCH"
    n=285;
    if method=="NONE", result=uint64(0:n-1); return; end
    if method=="BCH_CODEBLOCK"
        result=uint64([]); d=double(parameter);
        for base=0:d:18
            rows=min(d,19-base);
            for col=0:14, for row=0:rows-1, result(end+1)=uint64((base+row)*15+col); end, end %#ok<AGROW>
        end
        return
    end
    if method=="ROW_COLUMN", result=row_column(n,double(parameter)); return; end
    result=deterministic_shuffle(uint64(0:n-1),uint64(2026080407)); return
end
nSteps=306;
if method=="NONE", stepMap=uint64(0:nSteps-1);
elseif method=="SHORT_DEPTH_BLOCK"
    d=double(parameter); window=d*8; stepMap=uint64([]);
    for base=0:window:nSteps-1
        count=min(window,nSteps-base); local=row_column(count,min(d,count)); stepMap=[stepMap uint64(base)+local]; %#ok<AGROW>
    end
else
    span=double(parameter); stepMap=uint64([]);
    for base=0:span:nSteps-1
        count=min(span,nSteps-base); local=deterministic_shuffle(uint64(0:count-1),bitxor(bitxor(uint64(2026080417),uint64(base)),uint64(count)));
        stepMap=[stepMap uint64(base)+local]; %#ok<AGROW>
    end
end
result=zeros(1,2*numel(stepMap),'uint64'); result(1:2:end)=2*stepMap; result(2:2:end)=2*stepMap+1;
end

function result=row_column(n,rows)
cols=ceil(n/rows); result=uint64([]);
for col=0:cols-1, for row=0:rows-1, index=row*cols+col; if index<n, result(end+1)=uint64(index); end, end, end %#ok<AGROW>
end

function values=deterministic_shuffle(values,state)
if state==0, state=uint64(hex2dec('6a09e667f3bcc909')); end
for i=numel(values):-1:2
    state=bitxor(state,bitshift(state,13)); state=bitxor(state,bitshift(state,-7)); state=bitxor(state,bitshift(state,17));
    j=double(mod(state,uint64(i)))+1; tmp=values(i); values(i)=values(j); values(j)=tmp;
end
end

function result=mapping_sha256(values)
text=sprintf('%u,',values); md=java.security.MessageDigest.getInstance('SHA-256'); md.update(uint8(text));
bytes=typecast(md.digest(),'uint8'); result=string(lower(reshape(dec2hex(bytes,2).',1,[])));
end

function [decoded,tieCount]=explicit_viterbi(received,trellis,steps,initialState,finalState)
metrics=inf(1,64); metrics(initialState+1)=0; pred=-ones(steps,64); inputStore=-ones(steps,64); tieCount=0;
for time=1:steps
    next=inf(1,64);
    for state=0:63
        if ~isfinite(metrics(state+1)), continue; end
        for input=0:1
            ns=trellis.nextStates(state+1,input+1); decimal=trellis.outputs(state+1,input+1);
            o0=bitget(decimal,2); o1=bitget(decimal,1); y0=received(2*time-1); y1=received(2*time);
            candidate=metrics(state+1)+(y0-(1-2*o0))^2+(y1-(1-2*o1))^2;
            incumbent=next(ns+1); p=pred(time,ns+1); u=inputStore(time,ns+1);
            if isfinite(incumbent) && candidate==incumbent, tieCount=tieCount+1; end
            if ~isfinite(incumbent) || candidate<incumbent || (candidate==incumbent && (state<p || (state==p && input<u)))
                next(ns+1)=candidate; pred(time,ns+1)=state; inputStore(time,ns+1)=input;
            end
        end
    end
    minimum=min(next); metrics=next-minimum;
end
decoded=zeros(1,steps); state=finalState;
for time=steps:-1:1, decoded(time)=inputStore(time,state+1); state=pred(time,state+1); end
if state~=initialState, error('traceback initial state mismatch'); end
end

function value=ternary(condition,a,b)
if condition, value=a; else, value=b; end
end
