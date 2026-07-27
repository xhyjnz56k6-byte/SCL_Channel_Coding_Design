function stage13_burst_interleaving_validation_matlab_reference(cppCsv, permutationCsv, outputCsv, segmentedReferencePath)
    addpath(segmentedReferencePath);
    vectorOptions = detectImportOptions(cppCsv, Delimiter=",", TextType="string");
    vectorOptions = setvartype(vectorOptions, ...
        {'caseId','vectorId','interleaverMode','payloadBits','encodedBits', ...
         'interleavedBits','burstBits','deinterleavedBits', ...
         'cppRecoveredBits','cppStatus'}, 'string');
    vectors = readtable(cppCsv, vectorOptions);
    permutationOptions = detectImportOptions(permutationCsv, Delimiter=",", TextType="string");
    permutationOptions = setvartype(permutationOptions, ...
        {'caseId','interleaverMode'}, 'string');
    permutations = readtable(permutationCsv, permutationOptions);
    lookup15 = bch15_build_lookup_reference();

    rowCount = height(vectors);
    encodedMismatch = zeros(rowCount,1);
    interleavedBitMismatch = zeros(rowCount,1);
    burstPositionMismatch = zeros(rowCount,1);
    deinterleavedBitMismatch = zeros(rowCount,1);
    decodedPayloadMismatch = zeros(rowCount,1);
    statusMismatch = zeros(rowCount,1);
    matlabRecoveredBits = strings(rowCount,1);
    matlabStatus = strings(rowCount,1);

    for row = 1:rowCount
        caseIdText = char(vectors.caseId(row));
        modeText = char(vectors.interleaverMode(row));
        depth = vectors.interleaverDepth(row);
        payload = bits(char(vectors.payloadBits(row)));
        cppEncoded = bits(char(vectors.encodedBits(row)));
        cppInterleaved = bits(char(vectors.interleavedBits(row)));
        cppBurst = bits(char(vectors.burstBits(row)));
        cppDeinterleaved = bits(char(vectors.deinterleavedBits(row)));
        cppRecovered = bits(char(vectors.cppRecoveredBits(row)));

        matlabEncoded = encodeCase(caseIdText,payload);
        encodedMismatch(row) = sum(matlabEncoded ~= cppEncoded);

        selected = permutations.caseId == vectors.caseId(row) & ...
            permutations.interleaverMode == vectors.interleaverMode(row) & ...
            permutations.interleaverDepth == depth;
        group = permutations(selected,:);
        group = sortrows(group,'outputIndex');
        permutation = double(group.inputIndex)' + 1;
        if numel(permutation) ~= numel(cppEncoded)
            error("permutation length mismatch");
        end

        matlabInterleaved = matlabEncoded(permutation);
        interleavedBitMismatch(row) = ...
            sum(matlabInterleaved ~= cppInterleaved);
        startIndex = vectors.burstStart(row) + 1;
        burstLength = vectors.burstLengthBits(row);
        matlabBurst = matlabInterleaved;
        if burstLength > 0
            matlabBurst(startIndex:startIndex+burstLength-1) = ...
                xor(matlabBurst(startIndex:startIndex+burstLength-1),1);
        end
        observedChanged = find(matlabBurst ~= matlabInterleaved);
        if burstLength == 0
            burstPositionMismatch(row) = ~isempty(observedChanged);
        else
            expectedChanged = startIndex:startIndex+burstLength-1;
            burstPositionMismatch(row) = ...
                ~isequal(observedChanged(:)',expectedChanged);
        end

        matlabDeinterleaved = zeros(1,numel(matlabBurst));
        matlabDeinterleaved(permutation) = matlabBurst;
        deinterleavedBitMismatch(row) = ...
            sum(matlabDeinterleaved ~= cppDeinterleaved);

        [recovered,reportedSuccess] = ...
            decodeCase(caseIdText,matlabDeinterleaved,lookup15);
        matlabRecoveredBits(row) = string(char(recovered + double('0')));
        matlabStatus(row) = classifyStatus(payload,recovered,reportedSuccess);
        decodedPayloadMismatch(row) = sum(recovered ~= cppRecovered);
        statusMismatch(row) = matlabStatus(row) ~= vectors.cppStatus(row);
        if sum(matlabBurst ~= cppBurst) ~= 0
            burstPositionMismatch(row) = burstPositionMismatch(row) + ...
                sum(matlabBurst ~= cppBurst);
        end
    end

    caseId = vectors.caseId;
    vectorId = vectors.vectorId;
    interleaverMode = vectors.interleaverMode;
    interleaverDepth = vectors.interleaverDepth;
    passed = encodedMismatch == 0 & interleavedBitMismatch == 0 & ...
        burstPositionMismatch == 0 & deinterleavedBitMismatch == 0 & ...
        decodedPayloadMismatch == 0 & statusMismatch == 0;
    result = table(caseId,vectorId,interleaverMode,interleaverDepth, ...
        encodedMismatch,interleavedBitMismatch,burstPositionMismatch, ...
        deinterleavedBitMismatch,decodedPayloadMismatch,statusMismatch, ...
        matlabRecoveredBits,matlabStatus,passed);
    writetable(result,outputCsv);
    if ~all(passed)
        error("BLOCKED_STAGE13_BURST_INTERLEAVING_VALIDATION_MATLAB_REFERENCE");
    end
    fprintf("PASS_STAGE13_BURST_INTERLEAVING_VALIDATION_MATLAB_REFERENCE\n");
end

function value = bits(text)
    value = double(text) - double('0');
end

function encoded = encodeCase(id,payload)
    if contains(id,'_S15')
        oldId = 'BCH-S200';
        if startsWith(id,'K300'), oldId = 'BCH-S300'; end
        detail = bch15_segmented_encode_reference(oldId,payload);
        encoded = detail.encodedBits;
        return;
    end
    [n,k,payloads,shortening,~] = blockContract(id);
    encoded = [];
    offset = 0;
    for block = 1:numel(payloads)
        count = payloads(block);
        information = [zeros(1,shortening(block)), ...
            payload(offset+1:offset+count)];
        codeword = double(bchenc(gf(information),n,k).x);
        encoded = [encoded codeword(shortening(block)+1:end)]; %#ok<AGROW>
        offset = offset + count;
    end
end

function [recovered,reportedSuccess] = decodeCase(id,received,lookup15)
    if contains(id,'_S15')
        oldId = 'BCH-S200';
        if startsWith(id,'K300'), oldId = 'BCH-S300'; end
        detail = bch15_segmented_decode_reference(oldId,received,lookup15);
        recovered = detail.recoveredPayload;
        reportedSuccess = true;
        for block = 1:numel(detail.blockDetails)
            status = detail.blockDetails{block}.status;
            if ~(strcmp(status,'NO_ERROR') || ...
                    strcmp(status,'CORRECTED_SINGLE_ERROR'))
                reportedSuccess = false;
            end
        end
        return;
    end
    [n,k,payloads,shortening,encodedLengths] = blockContract(id);
    recovered = [];
    offset = 0;
    reportedSuccess = true;
    for block = 1:numel(payloads)
        shortened = received(offset+1:offset+encodedLengths(block));
        [decoded,numErrors] = bchdec( ...
            gf([zeros(1,shortening(block)),shortened]),n,k);
        decodedBits = double(decoded.x);
        recovered = [recovered ...
            decodedBits(shortening(block)+1:k)]; %#ok<AGROW>
        reportedSuccess = reportedSuccess && numErrors >= 0;
        offset = offset + encodedLengths(block);
    end
end

function status = classifyStatus(payload,recovered,reportedSuccess)
    if isequal(payload,recovered)
        status = "TRUE_SUCCESS";
    elseif reportedSuccess
        status = "MISCORRECTION";
    else
        status = "DECODER_FAILURE";
    end
end

function [n,k,payloads,shortening,encodedLengths] = blockContract(id)
    if contains(id,'M255K207')
        n=255;k=207;
        if startsWith(id,'K300')
            payloads=[150 150];shortening=[57 57];encodedLengths=[198 198];
        else
            payloads=200;shortening=7;encodedLengths=248;
        end
    elseif contains(id,'M511K421')
        n=511;k=421;
        if startsWith(id,'K300')
            payloads=300;shortening=121;encodedLengths=390;
        else
            payloads=200;shortening=221;encodedLengths=290;
        end
    elseif contains(id,'M511K385')
        n=511;k=385;
        if startsWith(id,'K300')
            payloads=300;shortening=85;encodedLengths=426;
        else
            payloads=200;shortening=185;encodedLengths=326;
        end
    else
        error("unsupported block case");
    end
end
