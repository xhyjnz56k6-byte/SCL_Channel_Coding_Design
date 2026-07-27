function stage14_burst_formal_matlab_reference(samplesCsv,outputCsv,segmentedReferencePath)
    addpath(segmentedReferencePath);
    options = detectImportOptions(samplesCsv,Delimiter=",",TextType="string");
    options = setvartype(options, ...
        {'caseId','vectorId','payloadBits','encodedBits','burstBits', ...
         'cppRecoveredBits','cppStatus'},'string');
    data = readtable(samplesCsv,options);
    table15 = bch15_build_lookup_reference();
    count = height(data);
    burstPositionMismatch = zeros(count,1);
    decodedPayloadMismatch = zeros(count,1);
    statusMismatch = zeros(count,1);
    matlabStatus = strings(count,1);
    matlabRecoveredBits = strings(count,1);
    for row=1:count
        id=char(data.caseId(row));
        payload=toBits(char(data.payloadBits(row)));
        encoded=toBits(char(data.encodedBits(row)));
        received=toBits(char(data.burstBits(row)));
        cppRecovered=toBits(char(data.cppRecoveredBits(row)));
        startIndex=data.burstStart(row)+1;
        burstLength=data.burstLengthBits(row);
        observed=find(received~=encoded);
        if burstLength==0
            burstPositionMismatch(row)=~isempty(observed);
        else
            expected=startIndex:startIndex+burstLength-1;
            burstPositionMismatch(row)=~isequal(observed(:)',expected);
        end
        [recovered,reportedSuccess]=decodeCase(id,received,table15);
        matlabRecoveredBits(row)=string(char(recovered+double('0')));
        matlabStatus(row)=classifyStatus(payload,recovered,reportedSuccess);
        decodedPayloadMismatch(row)=sum(recovered~=cppRecovered);
        statusMismatch(row)=matlabStatus(row)~=data.cppStatus(row);
    end
    caseId=data.caseId; vectorId=data.vectorId;
    burstLengthBits=data.burstLengthBits;
    passed=burstPositionMismatch==0 & decodedPayloadMismatch==0 & statusMismatch==0;
    output=table(caseId,vectorId,burstLengthBits,burstPositionMismatch, ...
        decodedPayloadMismatch,statusMismatch,matlabRecoveredBits,matlabStatus,passed);
    writetable(output,outputCsv);
    if ~all(passed),error("BLOCKED_STAGE14_BURST_FORMAL_MATLAB_REFERENCE");end
    fprintf("PASS_STAGE14_BURST_FORMAL_MATLAB_REFERENCE\n");
end

function value=toBits(text)
    value=double(text)-double('0');
end

function [recovered,reportedSuccess]=decodeCase(id,received,table15)
    if contains(id,'_S15')
        oldId='BCH-S200';if startsWith(id,'K300'),oldId='BCH-S300';end
        detail=bch15_segmented_decode_reference(oldId,received,table15);
        recovered=detail.recoveredPayload;reportedSuccess=true;
        for block=1:numel(detail.blockDetails)
            status=detail.blockDetails{block}.status;
            if ~(strcmp(status,'NO_ERROR')||strcmp(status,'CORRECTED_SINGLE_ERROR'))
                reportedSuccess=false;
            end
        end
        return;
    end
    [n,k,payloads,shortening,lengths]=blockContract(id);
    recovered=[];reportedSuccess=true;offset=0;
    for block=1:numel(payloads)
        shortened=received(offset+1:offset+lengths(block));
        [decoded,numErrors]=bchdec(gf([zeros(1,shortening(block)),shortened]),n,k);
        decodedBits=double(decoded.x);
        recovered=[recovered decodedBits(shortening(block)+1:k)]; %#ok<AGROW>
        reportedSuccess=reportedSuccess&&numErrors>=0;
        offset=offset+lengths(block);
    end
end

function status=classifyStatus(payload,recovered,reportedSuccess)
    if isequal(payload,recovered),status="TRUE_SUCCESS";
    elseif reportedSuccess,status="MISCORRECTION";
    else,status="DECODER_FAILURE";end
end

function [n,k,payloads,shortening,lengths]=blockContract(id)
    if contains(id,'M255K207')
        n=255;k=207;
        if startsWith(id,'K300'),payloads=[150 150];shortening=[57 57];lengths=[198 198];
        else,payloads=200;shortening=7;lengths=248;end
    elseif contains(id,'M511K421')
        n=511;k=421;
        if startsWith(id,'K300'),payloads=300;shortening=121;lengths=390;
        else,payloads=200;shortening=221;lengths=290;end
    elseif contains(id,'M511K385')
        n=511;k=385;
        if startsWith(id,'K300'),payloads=300;shortening=85;lengths=426;
        else,payloads=200;shortening=185;lengths=326;end
    else,error("unsupported block case");end
end

