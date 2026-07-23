function [payload,cnumerr] = official_decode_s200(hardBits)
% Decode one or more 285-bit hard-decision rows with official BCH(15,11).
if size(hardBits,2) ~= 285
    error('BCH16V:S200CodewordLength','S200 codeword must have 285 columns');
end
segments = reshape(double(hardBits).',15,[]).';
[decoded,segmentCnumerr] = bchdec(gf(segments),15,11,'end');
padded = reshape(double(decoded.x).',209,[]).';
payload = padded(:,1:200);
cnumerr = reshape(segmentCnumerr,19,[]).';
end

