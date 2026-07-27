function stage01_foundation_matlab_reference(inputCsv, outputCsv)
    data = readtable(inputCsv, VariableNamingRule="preserve");
    rate = data.actual_rate;
    ebn0 = data.ebn0_db;
    sigma2 = 1 ./ (2 .* rate .* 10.^(ebn0 ./ 10));
    sigma = sqrt(sigma2);
    noise = sigma .* data.z;
    transmitted = 1 - 2 .* data.bit;
    received = transmitted + noise;
    hard_decision = double(received < 0);
    snr_linear = 1 ./ sigma2;
    snr_db = ebn0 + 10 .* log10(2 .* rate);
    conversion_formula = repmat("SNR_dB = EbN0_dB + 10*log10(2*R)", height(data), 1);
    output = table(data.rowId, data.payloadLength, data.encodedLength, rate, ebn0, data.bit, data.z, ...
        sigma2, sigma, noise, transmitted, received, hard_decision, snr_linear, snr_db, ...
        conversion_formula);
    output.Properties.VariableNames = { ...
        'rowId','payloadLength','encodedLength','actual_rate','ebn0_db','bit','z', ...
        'sigma2','sigma','noise','transmitted','received','hard_decision','snr_linear', ...
        'snr_db','conversion_formula'};
    writetable(output, outputCsv);
    fprintf("PASS_STAGE01_FOUNDATION_MATLAB_REFERENCE\n");
end
