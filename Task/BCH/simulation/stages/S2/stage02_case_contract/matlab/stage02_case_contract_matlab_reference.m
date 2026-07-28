function stage02_case_contract_matlab_reference(casesCsv, outputCsv)
    options = detectImportOptions(casesCsv, Delimiter=",", VariableNamingRule="preserve", TextType="string");
    options = setvartype(options, ...
        {'caseId','payloadPerBlock','shorteningPerBlock','encodedLengthPerBlock'}, 'string');
    data = readtable(casesCsv, options);
    caseId = string(data{:, 1});
    payloadLength = data{:, 3};
    payloadPerBlock = string(data{:, 10});
    shorteningPerBlock = string(data{:, 12});
    encodedLengthPerBlock = string(data{:, 13});
    totalEncodedLength = data{:, 14};
    actualRate = data{:, 15};
    recomputedRate = payloadLength ./ totalEncodedLength;
    rateError = abs(actualRate - recomputedRate);
    payloadVectorSum = zeros(height(data), 1);
    encodedVectorSum = zeros(height(data), 1);
    shorteningVectorSum = zeros(height(data), 1);
    for row = 1:height(data)
        payloadVectorSum(row) = sum(sscanf(char(payloadPerBlock(row)), '%f|'));
        encodedVectorSum(row) = sum(sscanf(char(encodedLengthPerBlock(row)), '%f|'));
        shorteningVectorSum(row) = sum(sscanf(char(shorteningPerBlock(row)), '%f|'));
    end
    payloadSumPass = payloadVectorSum == payloadLength;
    encodedSumPass = encodedVectorSum == totalEncodedLength;
    ratePass = rateError <= 1e-15;
    passed = payloadSumPass & encodedSumPass & ratePass;
    output = table(caseId, payloadVectorSum, encodedVectorSum, shorteningVectorSum, ...
        recomputedRate, rateError, payloadSumPass, encodedSumPass, ratePass, passed);
    output.Properties.VariableNames = { ...
        'caseId','payloadVectorSum','encodedVectorSum','shorteningVectorSum', ...
        'recomputedRate','rateError','payloadSumPass','encodedSumPass','ratePass','passed'};
    writetable(output, outputCsv);
    if ~all(passed)
        error("BLOCKED_STAGE02_CASE_CONTRACT_MATLAB_REFERENCE");
    end
    fprintf("PASS_STAGE02_CASE_CONTRACT_MATLAB_REFERENCE\n");
end
