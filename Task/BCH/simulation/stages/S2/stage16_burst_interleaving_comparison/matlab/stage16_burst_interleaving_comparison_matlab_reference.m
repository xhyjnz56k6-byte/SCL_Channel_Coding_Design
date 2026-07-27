function stage16_burst_interleaving_comparison_matlab_reference(cppCsv,permutationCsv,pointsCsv,vectorOutputCsv,snrOutputCsv,segmentedReferencePath,stage13MatlabPath)
    addpath(stage13MatlabPath);
    stage13_burst_interleaving_validation_matlab_reference( ...
        cppCsv,permutationCsv,vectorOutputCsv,segmentedReferencePath);
    points = readtable(pointsCsv,'TextType','string');
    expected = points.targetSnrDb - 10 .* log10(caseRates(points.caseId));
    difference = abs(expected - points.derivedEbN0Db);
    passed = difference <= 1e-9;
    output = table(points.caseId,points.configurationId,points.snrIndex, ...
        points.targetSnrDb,points.derivedEbN0Db,expected,difference,passed, ...
        'VariableNames',{'caseId','configurationId','snrIndex', ...
        'targetSnrDb','cppDerivedEbN0Db','matlabDerivedEbN0Db', ...
        'absoluteDifference','passed'});
    writetable(output,snrOutputCsv);
    assert(all(passed),'Stage16 SNR conversion mismatch');
    fprintf("PASS_STAGE16_BURST_INTERLEAVING_COMPARISON_MATLAB_REFERENCE\n");
end

function rates = caseRates(ids)
    rates = zeros(height(ids),1);
    for index = 1:height(ids)
        switch ids(index)
            case "K200_S15"
                rates(index) = 200/285;
            case "K200_M255K207"
                rates(index) = 200/248;
            case "K200_M511K421"
                rates(index) = 200/290;
            case "K200_M511K385"
                rates(index) = 200/326;
            case "K300_S15"
                rates(index) = 300/420;
            case "K300_M255K207"
                rates(index) = 300/396;
            case "K300_M511K421"
                rates(index) = 300/390;
            case "K300_M511K385"
                rates(index) = 300/426;
            otherwise
                error("Unknown Stage16 case");
        end
    end
end
