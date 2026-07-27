function stage03_noiseless_matlab_reference(samplesCsv, outputCsv, segmentedReferencePath)
    addpath(segmentedReferencePath);
    options = detectImportOptions(samplesCsv, Delimiter=",", TextType="string");
    options = setvartype(options, {'caseId','payloadBits','cppEncodedBits','cppRecoveredBits'}, 'string');
    data = readtable(samplesCsv, options);
    table15 = bch15_build_lookup_reference();
    encodedMismatchBits = zeros(height(data),1);
    recoveredMismatchBits = zeros(height(data),1);
    matlabRecoveredMatchesPayload = false(height(data),1);
    for row = 1:height(data)
        id = char(data.caseId(row));
        payload = double(char(data.payloadBits(row))) - double('0');
        cppEncoded = double(char(data.cppEncodedBits(row))) - double('0');
        if contains(id, '_S15')
            oldId = 'BCH-S200';
            if startsWith(id, 'K300'), oldId = 'BCH-S300'; end
            encodedResult = bch15_segmented_encode_reference(oldId, payload);
            matlabEncoded = encodedResult.encodedBits;
            decodedResult = bch15_segmented_decode_reference(oldId, matlabEncoded, table15);
            matlabRecovered = decodedResult.recoveredPayload;
        else
            [n,k,blockPayloads,shortening] = blockContract(id);
            matlabEncoded = [];
            matlabRecovered = [];
            offset = 0;
            for block = 1:numel(blockPayloads)
                count = blockPayloads(block);
                blockPayload = payload(offset+1:offset+count);
                info = [zeros(1,shortening(block)), blockPayload];
                codeword = double(bchenc(gf(info),n,k).x);
                shortened = codeword(shortening(block)+1:end);
                matlabEncoded = [matlabEncoded shortened]; %#ok<AGROW>
                decoded = double(bchdec(gf([zeros(1,shortening(block)),shortened]),n,k).x);
                matlabRecovered = [matlabRecovered decoded(shortening(block)+1:k)]; %#ok<AGROW>
                offset = offset + count;
            end
        end
        encodedMismatchBits(row) = sum(matlabEncoded ~= cppEncoded);
        recoveredMismatchBits(row) = sum(matlabRecovered ~= payload);
        matlabRecoveredMatchesPayload(row) = isequal(matlabRecovered,payload);
    end
    caseId = data.caseId;
    sampleId = data.sampleId;
    passed = encodedMismatchBits == 0 & recoveredMismatchBits == 0 & matlabRecoveredMatchesPayload;
    output = table(caseId,sampleId,encodedMismatchBits,recoveredMismatchBits,matlabRecoveredMatchesPayload,passed);
    writetable(output,outputCsv);
    if ~all(passed), error("BLOCKED_STAGE03_NOISELESS_MATLAB_REFERENCE"); end
    fprintf("PASS_STAGE03_NOISELESS_MATLAB_REFERENCE\n");
end

function [n,k,payloads,shortening] = blockContract(id)
    if contains(id,'M255K207')
        n=255;k=207;
        if startsWith(id,'K300'),payloads=[150 150];shortening=[57 57];
        else,payloads=200;shortening=7;end
    elseif contains(id,'M511K421')
        n=511;k=421;
        if startsWith(id,'K300'),payloads=300;shortening=121;
        else,payloads=200;shortening=221;end
    elseif contains(id,'M511K385')
        n=511;k=385;
        if startsWith(id,'K300'),payloads=300;shortening=85;
        else,payloads=200;shortening=185;end
    else
        error("unsupported block case");
    end
end
