function run_bch16v_official_awgn(configPath,inputManifestPath,resultsDirectory,resume)
% BCH-16V official Communications Toolbox AWGN curve validation.
if nargin < 4, resume = false; end
config = jsondecode(fileread(configPath));
inputManifest = jsondecode(fileread(inputManifestPath));
if ~exist(resultsDirectory,'dir'), mkdir(resultsDirectory); end

environment = struct;
environment.matlabVersion = version;
environment.computerArchitecture = computer;
environment.communicationsToolboxInstalled = ~isempty(ver('comm'));
toolbox = ver('comm');
if isempty(toolbox)
    error('BLOCKED_BCH16V_COMMUNICATIONS_TOOLBOX_UNAVAILABLE');
end
environment.communicationsToolboxVersion = toolbox.Version;
environment.bchgenpolyAvailable = exist('bchgenpoly','file') == 2;
environment.bchencAvailable = exist('bchenc','file') == 2;
environment.bchdecAvailable = exist('bchdec','file') == 2;
environment.officialFunctionsUsed = {'bchgenpoly','bchenc','bchdec'};
writeText(fullfile(resultsDirectory,'matlab_environment.json'),jsonencode(environment,PrettyPrint=true));

[g15,t15] = bchgenpoly(15,11);
[g255,t255] = bchgenpoly(255,207,hex2dec('11D'));
parameterPath = fullfile(resultsDirectory,'official_parameter_audit.csv');
fid = fopen(parameterPath,'w');
fprintf(fid,'caseName,motherN,motherK,generatorDegree,correctionCapability,primitivePolynomial,generatorPolynomial,status\n');
fprintf(fid,'BCH-S200,15,11,%d,%d,default,%s,%s\n',numel(g15.x)-1,t15,char(double(g15.x)+'0'),passFail(numel(g15.x)-1==4 && t15==1));
fprintf(fid,'BCH-B200,255,207,%d,%d,0x11D,%s,%s\n',numel(g255.x)-1,t255,char(double(g255.x)+'0'),passFail(numel(g255.x)-1==48 && t255==6));
fclose(fid);
if numel(g15.x)-1 ~= 4 || t15 ~= 1 || numel(g255.x)-1 ~= 48 || t255 ~= 6
    error('BLOCKED_BCH16V_OFFICIAL_PARAMETER_MISMATCH');
end

validateOfficialEncoding(inputManifestPath,resultsDirectory);

summaryPath = fullfile(resultsDirectory,'matlab_official_formal_summary.csv');
representativePath = fullfile(resultsDirectory,'official_representative_decode_summary.csv');
pairedPath = fullfile(resultsDirectory,'paired_frame_error_contingency.csv');
if ~resume || ~isfile(summaryPath)
    writeText(summaryPath,sprintf(['caseName,ebn0Db,snrIndex,processedFrames,processedPayloadBits,decodedBitErrors,decodedFrameErrors,BER,FER,trueSuccessFrames,trueSuccessRate,' ...
        'officialCnumerrNegativeFrames,officialReportedCorrectedFrames,inputArtifactHash,configHash,withinCapabilityMismatchFrames,withinCapabilityMismatchBits,' ...
        'beyondCapabilityMismatchFrames,cppTrueSuccessMatlabFailure,cppFailureMatlabTrueSuccess,bothFrameErrorDifferentPayload,bothTrueSuccess,bothFrameError,sigma\n']));
    writeText(representativePath,sprintf('caseName,ebn0Db,snrIndex,processedFrames,withinCapabilityFrames,beyondCapabilityFrames,withinCapabilityMismatchFrames,withinCapabilityMismatchBits,beyondCapabilityMismatchFrames,status\n'));
    writeText(pairedPath,sprintf('caseName,ebn0Db,snrIndex,bothTrueSuccess,cppTrueSuccessMatlabFailure,cppFailureMatlabTrueSuccess,bothFrameError,bothFrameErrorDifferentPayload,mcnemarDiscordant,status\n'));
end
completed = strings(0,1);
if resume && isfile(summaryPath)
    prior = readtable(summaryPath,TextType='string');
    if ~isempty(prior)
        completed = string(prior.caseName) + "|" + string(prior.snrIndex);
    end
end

fprintf('BCH-16V execution plan\n');
fprintf('Cases: BCH-S200, BCH-B200\n');
selectedPointIndices = 1:numel(inputManifest.points);
if isfield(config,'pointIndices')
    selectedPointIndices = double(config.pointIndices(:)).';
    if isempty(selectedPointIndices) || any(selectedPointIndices < 1) || any(selectedPointIndices > numel(inputManifest.points)) || any(mod(selectedPointIndices,1) ~= 0)
        error('BCH16V:PointIndices','Invalid pointIndices');
    end
end
selectedPoints = inputManifest.points(selectedPointIndices);
fprintf('SNR points: %d | total frames: %d\n',numel(selectedPoints),sum([selectedPoints.processedFrames]));
fprintf('MATLAB: %s | Communications Toolbox: %s\n',version,toolbox.Version);
fprintf('Output: %s\n',resultsDirectory);
fprintf('Progress: %s refresh %.1fs checkpoint %d frames\n',passFail(config.progressEnabled),config.progressRefreshSeconds,config.checkpointIntervalFrames);

for selectedIndex = 1:numel(selectedPointIndices)
    pointIndex = selectedPointIndices(selectedIndex);
    point = inputManifest.points(pointIndex);
    key = string(point.caseName) + "|" + string(point.snrIndex);
    if any(completed == key), continue; end
    fprintf('[%d/%d] Run MATLAB %s %.1f dB\n',selectedIndex,numel(selectedPointIndices),point.caseName,point.ebn0Db);
    state = initialState(point,inputManifest,config,environment);
    checkpointPath = fullfile(resultsDirectory,'checkpoints',sprintf('%s_%03d.json',lower(strrep(point.caseName,'-','_')),point.snrIndex));
    if ~exist(fileparts(checkpointPath),'dir'), mkdir(fileparts(checkpointPath)); end
    if resume && isfile(checkpointPath)
        state = jsondecode(fileread(checkpointPath));
        validateCheckpoint(state,point,inputManifest,config,environment);
        state.resumeStartFrames = state.processedFrames;
    end
    started = tic;
    lastProgress = tic;
    while state.nextFrameIndex < point.processedFrames
        count = min(config.batchSize,double(point.processedFrames)-double(state.nextFrameIndex));
        [payload,z,cpp] = load_shared_input_batch(inputManifestPath,point,double(state.nextFrameIndex),count);
        if strcmp(point.caseName,'BCH-S200')
            encoded = official_encode_s200(payload);
        else
            encoded = official_encode_b200(payload);
        end
        sigma = sqrt(1/(2*double(point.frameRate)*10^(double(point.ebn0Db)/10)));
        if abs(sigma-double(point.noiseSigma)) > 1e-15
            error('BLOCKED_BCH16V_SIGMA_MISMATCH');
        end
        hard = (1-2*encoded + sigma*z) < 0;
        if strcmp(point.caseName,'BCH-S200')
            [decoded,cnumerr] = official_decode_s200(hard);
            within = cpp.maxSegmentWeight <= 1;
            cnumNegative = any(cnumerr < 0,2);
            cnumCorrected = any(cnumerr > 0,2) & ~cnumNegative;
        else
            [decoded,cnumerr] = official_decode_b200(hard);
            within = cpp.channelWeight <= 6;
            cnumNegative = cnumerr < 0;
            cnumCorrected = cnumerr > 0;
        end
        payload = logical(payload);
        decoded = logical(decoded);
        decodedErrors = sum(decoded ~= payload,2);
        matlabError = decodedErrors > 0;
        cppError = ~cpp.trueSuccess(:);
        decodedMismatchBits = sum(decoded ~= cpp.decodedPayload,2);
        decodedMismatch = decodedMismatchBits > 0;
        state.processedFrames = state.processedFrames + count;
        state.processedPayloadBits = state.processedPayloadBits + count*200;
        state.decodedBitErrors = state.decodedBitErrors + sum(decodedErrors);
        state.decodedFrameErrors = state.decodedFrameErrors + sum(matlabError);
        state.trueSuccessFrames = state.trueSuccessFrames + sum(~matlabError);
        state.officialCnumerrNegativeFrames = state.officialCnumerrNegativeFrames + sum(cnumNegative);
        state.officialReportedCorrectedFrames = state.officialReportedCorrectedFrames + sum(cnumCorrected);
        state.withinCapabilityFrames = state.withinCapabilityFrames + sum(within);
        state.beyondCapabilityFrames = state.beyondCapabilityFrames + sum(~within);
        state.withinCapabilityMismatchFrames = state.withinCapabilityMismatchFrames + sum(within(:) & decodedMismatch);
        state.withinCapabilityMismatchBits = state.withinCapabilityMismatchBits + sum(decodedMismatchBits(within(:)));
        state.beyondCapabilityMismatchFrames = state.beyondCapabilityMismatchFrames + sum(~within(:) & decodedMismatch);
        state.cppTrueSuccessMatlabFailure = state.cppTrueSuccessMatlabFailure + sum(~cppError & matlabError);
        state.cppFailureMatlabTrueSuccess = state.cppFailureMatlabTrueSuccess + sum(cppError & ~matlabError);
        state.bothFrameErrorDifferentPayload = state.bothFrameErrorDifferentPayload + sum(cppError & matlabError & decodedMismatch);
        state.bothTrueSuccess = state.bothTrueSuccess + sum(~cppError & ~matlabError);
        state.bothFrameError = state.bothFrameError + sum(cppError & matlabError);
        state.nextFrameIndex = state.nextFrameIndex + count;
        if mod(state.processedFrames,config.checkpointIntervalFrames) < count || state.nextFrameIndex == point.processedFrames
            state.checkpointCount = state.checkpointCount + 1;
            state.timestamp = char(datetime('now',TimeZone='UTC',Format='yyyy-MM-dd''T''HH:mm:ss''Z'''));
            writeText(checkpointPath,jsonencode(state,PrettyPrint=true));
        end
        if config.progressEnabled && (toc(lastProgress) >= config.progressRefreshSeconds || state.nextFrameIndex == point.processedFrames)
            elapsed = toc(started);
            speed = (state.processedFrames-state.resumeStartFrames)/max(elapsed,eps);
            eta = (double(point.processedFrames)-state.processedFrames)/max(speed,eps);
            fprintf('[BCH-16V][%s][%.1f dB] frames %d/%d bitErrors %d frameErrors %d BER %.3e FER %.3e speed %.1f frame/s elapsed %.1fs ETA %.1fs checkpoint %d\n', ...
                point.caseName,point.ebn0Db,state.processedFrames,point.processedFrames,state.decodedBitErrors,state.decodedFrameErrors, ...
                state.decodedBitErrors/max(state.processedPayloadBits,1),state.decodedFrameErrors/max(state.processedFrames,1),speed,elapsed,eta,state.checkpointCount);
            lastProgress = tic;
        end
    end
    if state.withinCapabilityMismatchFrames ~= 0 || state.withinCapabilityMismatchBits ~= 0
        error('BLOCKED_BCH16V_WITHIN_CAPABILITY_DECODE_MISMATCH');
    end
    appendSummary(summaryPath,point,state,inputManifest);
    appendRepresentative(representativePath,point,state);
    appendPaired(pairedPath,point,state);
end
fprintf('PASS_BCH16V_MATLAB_OFFICIAL_EXECUTION points=%d frames=%d\n',numel(selectedPoints),sum([selectedPoints.processedFrames]));
end

function validateOfficialEncoding(inputManifestPath,resultsDirectory)
inputDirectory = fileparts(inputManifestPath);
vectorPath = fullfile(inputDirectory,'cpp_official_encoding_vectors.csv');
options = detectImportOptions(vectorPath,TextType='string');
options = setvartype(options,{'caseName','vectorName','payloadBits','cppEncodedBits'},'string');
vectors = readtable(vectorPath,options);
frames = 0; bits = 0;
detailPath = fullfile(resultsDirectory,'official_encoding_compare_detail.csv');
fid = fopen(detailPath,'w');
fprintf(fid,'caseName,vectorName,mismatchBits,status\n');
for caseName = ["BCH-S200","BCH-B200"]
    indices = find(vectors.caseName == caseName);
    payload = double(char(vectors.payloadBits(indices))-'0');
    expected = char(vectors.cppEncodedBits(indices))-'0';
    if caseName == "BCH-S200"
        actual = official_encode_s200(payload);
    else
        actual = official_encode_b200(payload);
    end
    mismatch = sum(actual ~= expected,2);
    frames = frames + sum(mismatch ~= 0);
    bits = bits + sum(mismatch);
    for j = 1:numel(indices)
        i = indices(j);
        fprintf(fid,'%s,%s,%d,%s\n',vectors.caseName(i),vectors.vectorName(i),mismatch(j),passFail(mismatch(j)==0));
    end
end
fclose(fid);
fid = fopen(fullfile(resultsDirectory,'official_encoding_compare_summary.csv'),'w');
fprintf(fid,'vectors,encodedMismatchFrames,encodedMismatchBits,status\n%d,%d,%d,%s\n',height(vectors),frames,bits,passFail(frames==0 && bits==0));
fclose(fid);
if frames ~= 0 || bits ~= 0
    error('BLOCKED_BCH16V_OFFICIAL_ENCODING_MISMATCH');
end
end

function state = initialState(point,inputManifest,config,environment)
state = struct('caseName',point.caseName,'ebn0Db',point.ebn0Db,'snrIndex',point.snrIndex, ...
    'totalFrames',point.processedFrames,'nextFrameIndex',0,'processedFrames',0,'processedPayloadBits',0, ...
    'decodedBitErrors',0,'decodedFrameErrors',0,'trueSuccessFrames',0,'officialCnumerrNegativeFrames',0, ...
    'officialReportedCorrectedFrames',0,'withinCapabilityFrames',0,'beyondCapabilityFrames',0, ...
    'withinCapabilityMismatchFrames',0,'withinCapabilityMismatchBits',0,'beyondCapabilityMismatchFrames',0, ...
    'cppTrueSuccessMatlabFailure',0,'cppFailureMatlabTrueSuccess',0,'bothFrameErrorDifferentPayload',0, ...
    'bothTrueSuccess',0,'bothFrameError',0,'checkpointCount',0,'resumeStartFrames',0, ...
    'configHash',config.configHash,'inputArtifactHash',point.noiseSha256,'matlabVersion',environment.matlabVersion, ...
    'toolboxVersion',environment.communicationsToolboxVersion,'bitOrder','lsb_first','frameRate',point.frameRate, ...
    'primitivePolynomial','0x11D','timestamp','');
end

function validateCheckpoint(state,point,inputManifest,config,environment) %#ok<INUSD>
valid = strcmp(state.caseName,point.caseName) && state.snrIndex == point.snrIndex && ...
    state.totalFrames == point.processedFrames && strcmp(state.inputArtifactHash,point.noiseSha256) && ...
    strcmp(state.configHash,config.configHash) && strcmp(state.matlabVersion,environment.matlabVersion) && ...
    strcmp(state.toolboxVersion,environment.communicationsToolboxVersion) && strcmp(state.bitOrder,'lsb_first') && ...
    abs(state.frameRate-point.frameRate) < 1e-15 && strcmp(state.primitivePolynomial,'0x11D');
if ~valid, error('BCH16V:CheckpointMismatch','Checkpoint is incompatible with current configuration'); end
state.resumeStartFrames = state.processedFrames; %#ok<NASGU>
end

function appendSummary(path,point,state,inputManifest)
fid=fopen(path,'a'); c=onCleanup(@()fclose(fid));
fprintf(fid,'%s,%.17g,%d,%d,%d,%d,%d,%.17g,%.17g,%d,%.17g,%d,%d,%s,%s,%d,%d,%d,%d,%d,%d,%d,%d,%.17g\n', ...
    point.caseName,point.ebn0Db,point.snrIndex,state.processedFrames,state.processedPayloadBits,state.decodedBitErrors,state.decodedFrameErrors, ...
    state.decodedBitErrors/state.processedPayloadBits,state.decodedFrameErrors/state.processedFrames,state.trueSuccessFrames,state.trueSuccessFrames/state.processedFrames, ...
    state.officialCnumerrNegativeFrames,state.officialReportedCorrectedFrames,point.noiseSha256,inputManifest.formalSummarySha256, ...
    state.withinCapabilityMismatchFrames,state.withinCapabilityMismatchBits,state.beyondCapabilityMismatchFrames,state.cppTrueSuccessMatlabFailure, ...
    state.cppFailureMatlabTrueSuccess,state.bothFrameErrorDifferentPayload,state.bothTrueSuccess,state.bothFrameError,point.noiseSigma);
end

function appendRepresentative(path,point,state)
fid=fopen(path,'a'); c=onCleanup(@()fclose(fid));
fprintf(fid,'%s,%.17g,%d,%d,%d,%d,%d,%d,%d,%s\n',point.caseName,point.ebn0Db,point.snrIndex,state.processedFrames, ...
    state.withinCapabilityFrames,state.beyondCapabilityFrames,state.withinCapabilityMismatchFrames,state.withinCapabilityMismatchBits, ...
    state.beyondCapabilityMismatchFrames,passFail(state.withinCapabilityMismatchFrames==0));
end

function appendPaired(path,point,state)
fid=fopen(path,'a'); c=onCleanup(@()fclose(fid));
fprintf(fid,'%s,%.17g,%d,%d,%d,%d,%d,%d,%d,%s\n',point.caseName,point.ebn0Db,point.snrIndex,state.bothTrueSuccess, ...
    state.cppTrueSuccessMatlabFailure,state.cppFailureMatlabTrueSuccess,state.bothFrameError,state.bothFrameErrorDifferentPayload, ...
    state.cppTrueSuccessMatlabFailure+state.cppFailureMatlabTrueSuccess,passFail(true));
end

function writeText(path,text)
fid=fopen(path,'w'); if fid<0,error('BCH16V:Write','Cannot write %s',path);end
c=onCleanup(@()fclose(fid)); fwrite(fid,text,'char');
end

function text = passFail(value)
if value, text='PASS'; else, text='FAIL'; end
end
