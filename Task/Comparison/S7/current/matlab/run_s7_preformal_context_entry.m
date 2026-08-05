scriptDir = fileparts(mfilename('fullpath'));
outputDir = fullfile(scriptDir, '..', '..', 'stage08_cpp_matlab_smoke', 'results_preformal_context_reuse');
run_s7_smoke_reference(outputDir);

