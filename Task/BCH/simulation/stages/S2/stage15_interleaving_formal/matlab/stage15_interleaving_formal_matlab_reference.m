function stage15_interleaving_formal_matlab_reference(cppCsv,permutationCsv,outputCsv,segmentedReferencePath,stage13MatlabPath)
    addpath(stage13MatlabPath);
    stage13_burst_interleaving_validation_matlab_reference( ...
        cppCsv,permutationCsv,outputCsv,segmentedReferencePath);
    fprintf("PASS_STAGE15_INTERLEAVING_FORMAL_MATLAB_REFERENCE\n");
end

