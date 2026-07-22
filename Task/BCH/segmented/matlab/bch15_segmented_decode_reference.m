function result = bch15_segmented_decode_reference(caseName, received, table)
config=bch15_segmented_config_reference(caseName); received=bch15_validate_bits(received,config.encodedLength,'received');
result.config=config; result.recoveredPaddedMessage=zeros(1,config.payloadLength+config.fillerBits); result.blockDetails=cell(1,config.blockCount);
result.frameDetail=struct('totalBlocks',0,'noErrorBlocks',0,'correctedBlocks',0,'lookupHitBlocks',0,'lookupMissBlocks',0,'postCheckFailedBlocks',0,'unrecognizedSyndromeBlocks',0);
for b=0:config.blockCount-1
    d=bch15_lookup_decode_reference(received(15*b+1:15*b+15),table); result.blockDetails{b+1}=d; result.recoveredPaddedMessage(11*b+1:11*b+11)=d.decodedMessage; result.frameDetail.totalBlocks=result.frameDetail.totalBlocks+1;
    if strcmp(d.status,'NO_ERROR'), result.frameDetail.noErrorBlocks=result.frameDetail.noErrorBlocks+1; end
    if strcmp(d.status,'CORRECTED_SINGLE_ERROR'), result.frameDetail.correctedBlocks=result.frameDetail.correctedBlocks+1; end
    if d.lookupHit, result.frameDetail.lookupHitBlocks=result.frameDetail.lookupHitBlocks+1; end
    if strcmp(d.status,'UNRECOGNIZED_SYNDROME'), result.frameDetail.lookupMissBlocks=result.frameDetail.lookupMissBlocks+1; result.frameDetail.unrecognizedSyndromeBlocks=result.frameDetail.unrecognizedSyndromeBlocks+1; end
    if strcmp(d.status,'POST_CHECK_FAILED'), result.frameDetail.postCheckFailedBlocks=result.frameDetail.postCheckFailedBlocks+1; end
end
result.recoveredPayload=result.recoveredPaddedMessage(1:config.payloadLength);
end
