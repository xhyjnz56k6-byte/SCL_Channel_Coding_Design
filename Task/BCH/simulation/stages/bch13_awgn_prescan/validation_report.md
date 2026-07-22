# BCH-13 validation report

Functional range: `2bf89bed2fb44c2f4f9c2c3ec54cf061f863b464...d4e7a56f84a78d458f54979bdd97a66d7f4f02d3`.

The full 0.0–10.0 dB, 0.5 dB grid ran without adjustment: 84 unique case-points, 2,000 fixed
frames per point, 168,000 total frames. All result fields were finite, point keys were unique, and
raw accounting passed. The 84 latest progress records are COMPLETE.

Measured formal recommendations are:

- BCH-S200: 4.5–8.5 dB, 0.2 dB step; measured FER landmarks 0.578, 0.1415, 0.009, 0.0005.
- BCH-B200: 3.5–6.0 dB, 0.2 dB step; measured FER landmarks 0.5725, 0.1365, 0.0045, 0 observed.
- BCH-S300: 5.0–9.0 dB, 0.2 dB step; measured FER landmarks 0.5125, 0.0865, 0.0175, 0.001.
- BCH-B300: 4.0–5.5 dB, 0.2 dB step; measured FER landmarks 0.364, 0.119, 0.019, 0.0015.

No target FER is extrapolated. A zero observation remains an observation, not a claim of true FER
zero. Six matplotlib 3.10.7 PNGs were generated and visually inspected; figure data, hashes, PNG
magic, and the zero-observation policies passed. Non-PNG plot artifact count is zero.

Gate: `PASS_BCH13_AWGN_PRESCAN`.
