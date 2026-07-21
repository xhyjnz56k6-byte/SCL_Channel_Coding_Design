# Common-04 Result Schema

`summary.csv` uses schema:

```text
common04.result_summary.v1
```

Required columns:

```text
schemaVersion,experimentId,stage,codeType,caseName,payloadLength,encodedLength,codeRate,ebN0_dB,snrIndex,processedFrames,totalPayloadBits,bitErrors,frameErrors,successfulFrames,ber,fer,successRate,avgEncodeTimeUs,avgChannelTimeUs,avgDecodeTimeUs,maxDecodeTimeUs,avgRecoveryTimeUs,avgTotalTimeUs,maxTotalTimeUs,stopReason,framePoolId,noisePoolId,configHash
```

`metadata.json` uses schema:

```text
common04.metadata.v1
```

`createdTime` is allowed only in runtime metadata. It must not enter `configHash`, `noisePoolId` or noise-pool `overallHash`.

BER and FER compare only `originalPayload` and `recoveredPayload`.
