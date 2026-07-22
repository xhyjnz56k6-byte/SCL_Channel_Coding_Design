# BCH-06 validation report

functionalGate: PASS_BCH06_SEGMENTED_MATLAB_FUNCTIONAL
singleBlockCrossCheckGate: PASS_BCH06_CPP_MATLAB_SINGLE_BLOCK_CROSS_CHECK
segmentedCrossCheckGate: PASS_BCH06_CPP_MATLAB_SEGMENTED_CROSS_CHECK
invalidInputAuditGate: PASS_BCH06_MATLAB_INVALID_INPUT_AUDIT
fixedMultiErrorGate: PASS_BCH06_FIXED_MULTI_ERROR_CROSSCHECK
auditGate: PASS_BCH06_SEGMENTED_MATLAB_AUDIT
finalGate: PASS_BCH06_SEGMENTED_MATLAB_REFERENCE

encoderCases=2048, mismatch=0
singleErrorDecodeCases=30720, mismatch=0
segmentedNoiselessFrames=208, mismatch=0
segmentedSingleErrorCases=705, mismatch=0
multiBlockSingleErrorCases=8, mismatch=0
sameBlockDoubleErrorCases=12, mismatch=0
reportedSuccessWrongBlockInformation=12
reportedSuccessWrongOriginalPayload=9
fillerOnlyInformationMismatch=3
fillerBoundaryCases=30, mismatch=0
failureStatusRetentionCases=4, mismatch=0
framePoolAuditCases=200, mismatch=0
fixedMultiErrorCases=96, mismatch=0
matlabInvalidInputCases=20, failure=0

Common regression:
- test_common04_random_policy.exe exitCode=0 PASS
- test_common04_gaussian_noise.exe exitCode=0 PASS
- test_common04_modulation_awgn.exe exitCode=0 PASS
- test_common04_metrics_control.exe exitCode=0 PASS
- test_common04_checkpoint.exe exitCode=0 PASS
- test_common04_integration.exe exitCode=0 PASS

Scope checks:
- Task/Common diff: empty
- historical BCH-01..BCH-05 Stage diff: empty
- BCH-07/AWGN/whole-block/BM/Chien implementation scan: no implementation added
