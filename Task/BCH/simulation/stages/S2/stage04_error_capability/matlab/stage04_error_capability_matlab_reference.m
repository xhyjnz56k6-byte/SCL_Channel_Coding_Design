function stage04_error_capability_matlab_reference(samplesCsv, outputCsv, segmentedReferencePath)
    addpath(segmentedReferencePath);
    options = detectImportOptions(samplesCsv, Delimiter=",", TextType="string");
    options = setvartype(options, ...
        {'caseId','payloadBits','encodedBits','receivedBits','cppRecoveredBits','cppStatus'}, 'string');
    data = readtable(samplesCsv, options);
    table15 = bch15_build_lookup_reference();
    recoveredMismatchBits = zeros(height(data),1);
    cppRecoveredMismatchBits = zeros(height(data),1);
    matlabTrueSuccess = false(height(data),1);
    for row=1:height(data)
        id=char(data.caseId(row));
        payload=double(char(data.payloadBits(row)))-double('0');
        received=double(char(data.receivedBits(row)))-double('0');
        cppRecovered=double(char(data.cppRecoveredBits(row)))-double('0');
        if contains(id,'_S15')
            oldId='BCH-S200'; if startsWith(id,'K300'),oldId='BCH-S300';end
            decoded=bch15_segmented_decode_reference(oldId,received,table15);
            recovered=decoded.recoveredPayload;
        else
            [n,k,payloads,shortening,encodedLengths]=blockContract(id);
            recovered=[]; offset=0;
            for block=1:numel(payloads)
                shortened=received(offset+1:offset+encodedLengths(block));
                decoded=double(bchdec(gf([zeros(1,shortening(block)),shortened]),n,k).x);
                recovered=[recovered decoded(shortening(block)+1:k)]; %#ok<AGROW>
                offset=offset+encodedLengths(block);
            end
        end
        recoveredMismatchBits(row)=sum(recovered~=payload);
        cppRecoveredMismatchBits(row)=sum(cppRecovered~=payload);
        matlabTrueSuccess(row)=isequal(recovered,payload);
    end
    caseId=data.caseId; patternId=data.patternId; errorWeight=data.errorWeight;
    cppStatus=data.cppStatus;
    passed=recoveredMismatchBits==0 & cppRecoveredMismatchBits==0 & ...
        matlabTrueSuccess & cppStatus=="TRUE_SUCCESS";
    output=table(caseId,patternId,errorWeight,cppStatus,recoveredMismatchBits, ...
        cppRecoveredMismatchBits,matlabTrueSuccess,passed);
    writetable(output,outputCsv);
    if ~all(passed),error("BLOCKED_STAGE04_ERROR_CAPABILITY_MATLAB_REFERENCE");end
    fprintf("PASS_STAGE04_ERROR_CAPABILITY_MATLAB_REFERENCE\n");
end

function [n,k,payloads,shortening,encodedLengths]=blockContract(id)
    if contains(id,'M255K207')
        n=255;k=207;
        if startsWith(id,'K300'),payloads=[150 150];shortening=[57 57];encodedLengths=[198 198];
        else,payloads=200;shortening=7;encodedLengths=248;end
    elseif contains(id,'M511K421')
        n=511;k=421;
        if startsWith(id,'K300'),payloads=300;shortening=121;encodedLengths=390;
        else,payloads=200;shortening=221;encodedLengths=290;end
    elseif contains(id,'M511K385')
        n=511;k=385;
        if startsWith(id,'K300'),payloads=300;shortening=85;encodedLengths=426;
        else,payloads=200;shortening=185;encodedLengths=326;end
    else,error("unsupported block case");end
end
