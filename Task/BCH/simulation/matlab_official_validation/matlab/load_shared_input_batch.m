function [payload,standardNoise,cppReference] = load_shared_input_batch(inputManifestPath,point,frameStart,frameCount)
% Stream one batch from the neutral payload/noise artifacts.
persistent cachedManifestPath cachedPacked cachedPayloadManifest
inputManifestPath = char(inputManifestPath);
manifest = jsondecode(fileread(inputManifestPath));
if isempty(cachedManifestPath) || ~strcmp(cachedManifestPath,manifest.payloadManifest)
    cachedPayloadManifest = jsondecode(fileread(manifest.payloadManifest));
    directory = fileparts(manifest.payloadManifest);
    cachedPacked = zeros(cachedPayloadManifest.totalFrames,cachedPayloadManifest.bytesPerFrame,'uint8');
    for i = 1:numel(cachedPayloadManifest.shards)
        shard = cachedPayloadManifest.shards(i);
        fid = fopen(fullfile(directory,shard.fileName),'rb','ieee-le');
        if fid < 0, error('BCH16V:PayloadOpen','Cannot open payload shard'); end
        cleanup = onCleanup(@() fclose(fid));
        raw = fread(fid,[cachedPayloadManifest.bytesPerFrame,shard.frameCount],'uint8=>uint8').';
        clear cleanup
        first = double(shard.startFrame) + 1;
        cachedPacked(first:first+double(shard.frameCount)-1,:) = raw;
    end
    cachedManifestPath = manifest.payloadManifest;
end
indices = frameStart + (1:frameCount);
packed = cachedPacked(indices,:);
payload = false(frameCount,200);
for bitIndex = 0:199
    payload(:,bitIndex+1) = bitget(packed(:,floor(bitIndex/8)+1),mod(bitIndex,8)+1) ~= 0;
end

inputDirectory = fileparts(inputManifestPath);
noisePath = fullfile(inputDirectory,point.noiseFile);
fid = fopen(noisePath,'rb','ieee-le');
if fid < 0, error('BCH16V:NoiseOpen','Cannot open standard Gaussian input'); end
cleanup = onCleanup(@() fclose(fid));
status = fseek(fid,frameStart*double(point.encodedLength)*8,'bof');
if status ~= 0, error('BCH16V:NoiseSeek','Cannot seek standard Gaussian input'); end
standardNoise = fread(fid,[double(point.encodedLength),frameCount],'double=>double').';
if size(standardNoise,1) ~= frameCount
    error('BCH16V:NoiseShortRead','Short read from standard Gaussian input');
end
clear cleanup

referencePath = fullfile(inputDirectory,point.cppReferenceFile);
fid = fopen(referencePath,'rb','ieee-le');
if fid < 0, error('BCH16V:ReferenceOpen','Cannot open C++ comparison reference'); end
cleanup = onCleanup(@() fclose(fid));
status = fseek(fid,frameStart*double(point.cppReferenceRecordBytes),'bof');
if status ~= 0, error('BCH16V:ReferenceSeek','Cannot seek C++ comparison reference'); end
raw = fread(fid,[double(point.cppReferenceRecordBytes),frameCount],'uint8=>uint8');
if size(raw,2) ~= frameCount
    error('BCH16V:ReferenceShortRead','Short read from C++ comparison reference');
end
clear cleanup
cppReference.frameIndex = double(raw(1,:)) + 256*double(raw(2,:)) + 65536*double(raw(3,:)) + 16777216*double(raw(4,:));
cppReference.channelWeight = double(raw(5,:)) + 256*double(raw(6,:));
cppReference.decodedErrors = double(raw(7,:)) + 256*double(raw(8,:));
cppReference.trueSuccess = raw(9,:) ~= 0;
cppReference.reportedSuccess = raw(10,:) ~= 0;
cppReference.miscorrected = raw(11,:) ~= 0;
cppReference.decoderFailure = raw(12,:) ~= 0;
cppReference.maxSegmentWeight = double(raw(13,:));
decodedPacked = raw(14:38,:).';
cppReference.decodedPayload = false(frameCount,200);
for bitIndex = 0:199
    cppReference.decodedPayload(:,bitIndex+1) = bitget(decodedPacked(:,floor(bitIndex/8)+1),mod(bitIndex,8)+1) ~= 0;
end
end

