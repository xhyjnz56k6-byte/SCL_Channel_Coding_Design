# stage08_multipath_formal_common_snr Conclusion

鏈粨璁哄彧浣跨敤缁熶竴 `waveformSnrDb=0:0.5:18` 缃戞牸涓嬬殑鍚?SNR 妯悜姣旇緝锛涙棫 Stage08 鏍囪涓?`LEGACY_WIDE_GRID_FORMAL`锛屼笉浣滀负鏈€缁堟í鍚戞帓鍚嶄緷鎹€?

Error-floor 澶勭悊瑙勫垯锛氭寮忕粨鏋?CSV 涓殑 `ber=0` / `fer=0` 淇濇寔鍘熷鏁存暟璁℃暟鍚箟锛涘湪缁撹鍜岄珮 SNR 鎺掑悕涓紝闆堕敊璇偣鏍囪涓?`ZERO_OBSERVED_CENSORED`锛屽彧璇存槑鍦ㄥ綋鍓嶅抚鏁颁笅鏈娴嬪埌閿欒锛屽苟浣跨敤鍗曚晶 95% 涓婄晫 `3/N` 缁欏嚭鍙鏌ョ害鏉燂紝涓嶈兘褰撲綔鐪熷疄 error floor 涓?0銆?

`miscorrectionFrames` 涓?`undetectedErrorFrames` 鍦ㄥ綋鍓嶈瘧鐮佹帴鍙ｈ涔変笅鏄悓涓€浜嬩欢闆嗗悎鐨勪袱涓涔夋爣绛撅紝涓嶆槸浜掓枼绫诲埆銆?

## 200 bit

- 浣?SNR 瑙傛祴 BER 鏈€浼橈細K200_M511K421锛涜娴?FER 鏈€浼橈細K200_S15銆?
- 涓?SNR 瑙傛祴 BER 鏈€浼橈細K200_M511K385锛涜娴?FER 鏈€浼橈細K200_M511K385銆?
- 楂?SNR error-floor-aware BER 鍊欓€夌粍锛欿200_M255K207;K200_M511K385;K200_M511K421锛?5% 涓婄晫绾︽潫 <= 3e-07銆?
- 楂?SNR error-floor-aware FER 鍊欓€夌粍锛欿200_M255K207;K200_M511K385;K200_M511K421锛?5% 涓婄晫绾︽潫 <= 6e-05銆?
- 鐮佺巼浼樺厛锛欿200_M255K207锛汢CH 璇戠爜鏃跺欢浼樺厛锛欿200_S15锛汳MSE 鍧囪　鏃跺欢浼樺厛锛欿200_S15銆?
- 涓嶅瓨鍦ㄨ劚绂?SNR 宸ヤ綔鍖洪棿鍜屾湁闄愭牱鏈?censoring 鐨勫崟涓€缁濆鏈€浼樻柟妗堛€?

## 300 bit

- 浣?SNR 瑙傛祴 BER 鏈€浼橈細K300_M255K207锛涜娴?FER 鏈€浼橈細K300_S15銆?
- 涓?SNR 瑙傛祴 BER 鏈€浼橈細K300_M511K385锛涜娴?FER 鏈€浼橈細K300_M511K385銆?
- 楂?SNR error-floor-aware BER 鍊欓€夌粍锛欿300_M255K207;K300_M511K385;K300_M511K421锛?5% 涓婄晫绾︽潫 <= 2e-07銆?
- 楂?SNR error-floor-aware FER 鍊欓€夌粍锛欿300_M255K207;K300_M511K385;K300_M511K421锛?5% 涓婄晫绾︽潫 <= 6e-05銆?
- 鐮佺巼浼樺厛锛欿300_M511K421锛汢CH 璇戠爜鏃跺欢浼樺厛锛欿300_S15锛汳MSE 鍧囪　鏃跺欢浼樺厛锛欿300_M255K207銆?
- 涓嶅瓨鍦ㄨ劚绂?SNR 宸ヤ綔鍖洪棿鍜屾湁闄愭牱鏈?censoring 鐨勫崟涓€缁濆鏈€浼樻柟妗堛€?
