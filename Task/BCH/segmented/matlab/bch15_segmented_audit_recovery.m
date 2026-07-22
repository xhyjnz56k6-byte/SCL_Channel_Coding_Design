function audit = bch15_segmented_audit_recovery(payload, result)
audit.paddedInformationMismatch = sum(result.recoveredPaddedMessage ~= [payload zeros(1,result.config.fillerBits)]);
audit.recoveredPayloadMismatch = sum(result.recoveredPayload ~= payload);
end
