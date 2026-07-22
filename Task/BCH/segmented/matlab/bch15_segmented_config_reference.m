function config = bch15_segmented_config_reference(caseName)
if strcmp(caseName,'BCH-S200'), config = struct('name','BCH-S200','payloadLength',200,'blockCount',19,'fillerBits',9,'encodedLength',285); elseif strcmp(caseName,'BCH-S300'), config = struct('name','BCH-S300','payloadLength',300,'blockCount',28,'fillerBits',8,'encodedLength',420); else, error('BCH06:InvalidCase','case must be BCH-S200 or BCH-S300.'); end
config.blockPayloadLength = 11; config.encodedBlockLength = 15;
end
