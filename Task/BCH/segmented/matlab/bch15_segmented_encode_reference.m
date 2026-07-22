function result = bch15_segmented_encode_reference(caseName, payload)
config = bch15_segmented_config_reference(caseName); payload = bch15_validate_bits(payload, config.payloadLength, 'payload');
result.config=config; result.payloadBits=payload; result.paddedMessageBits=[payload zeros(1,config.fillerBits)]; result.encodedBits=zeros(1,config.encodedLength);
for b=0:config.blockCount-1
    result.encodedBits(15*b+1:15*b+15)=bch15_encode_reference(result.paddedMessageBits(11*b+1:11*b+11));
end
end
