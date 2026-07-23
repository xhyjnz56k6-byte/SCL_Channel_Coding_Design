function [payload,cnumerr] = official_decode_b200(hardBits)
% Decode shortened BCH-B200 by restoring seven known-zero mother positions.
if size(hardBits,2) ~= 248
    error('BCH16V:B200CodewordLength','B200 codeword must have 248 columns');
end
motherReceived = [zeros(size(hardBits,1),7), double(hardBits)];
[decoded,cnumerr] = bchdec(gf(motherReceived),255,207,'end');
motherInformation = double(decoded.x);
payload = motherInformation(:,8:207);
end

