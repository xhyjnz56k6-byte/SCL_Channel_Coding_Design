function encoded = official_encode_b200(payload)
% Encode shortened BCH-B200 through the official BCH(255,207) mother code.
if size(payload,2) ~= 200
    error('BCH16V:B200PayloadLength','B200 payload must have 200 columns');
end
motherInformation = [zeros(size(payload,1),7), double(payload)];
motherCodeword = double(bchenc(gf(motherInformation),255,207,'end').x);
encoded = motherCodeword(:,8:255);
end

