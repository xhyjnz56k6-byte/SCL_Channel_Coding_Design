#pragma once

#include "cc/block_encoder.hpp"
#include "cc/soft_viterbi.hpp"
#include "cc/trellis.hpp"
#include "s4_ldpc.hpp"

#include <complex>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace s5 {

constexpr std::size_t kPayloadLength = 300;
constexpr double kNoiselessSoftMagnitude = 100.0;
constexpr std::uint64_t kPayloadSeed = 2026072001ULL;
constexpr std::uint64_t kNoiseSeed = 2026072004ULL;
constexpr std::uint64_t kNoisePolicyVersion = 2ULL;
constexpr const char* kComplexNoisePolicy = "s5_complex_pair_v1";

enum class Scheme { CcR23, CcR12, LdpcN480, LdpcN640 };
enum class Channel { Awgn, Multipath, Cfo, Doppler, Blockage10, Blockage5, Burst };

struct SchemeSpec {
    Scheme scheme;
    std::string id;
    std::string comparisonGroup;
    std::size_t transmittedLength;
    double actualRate;
    double ldpcAlpha;
};

struct ChannelTrace {
    std::vector<std::complex<double>> tx;
    std::vector<std::complex<double>> impaired;
    std::vector<std::complex<double>> rx;
    std::vector<double> llr;
    std::vector<double> phase;
    std::vector<double> epsilon;
    std::vector<double> mask;
    std::vector<double> equalized;
    std::vector<double> gain;
    std::vector<double> variance;
    std::size_t damageStart = 0;
    std::size_t damageLength = 0;
    double relativeStart = 0.0;
    double sigmaSquared = 0.0;
    double channelImpairmentTimeUs = 0.0;
    double awgnTimeUs = 0.0;
    double equalizationTimeUs = 0.0;
    double projectionTimeUs = 0.0;
    double llrGenerationTimeUs = 0.0;
    double channelProcessingTimeUs = 0.0;
};

struct DecodeOutcome {
    std::vector<std::uint8_t> payload;
    bool decoderFailure = false;
    int usedIterations = 0;
    int finalSyndromeWeight = 0;
};

struct CodecContext {
    CodecContext();
    CodecContext(const CodecContext&) = delete;
    CodecContext& operator=(const CodecContext&) = delete;

    scl::cc::Trellis ccTrellis;
    scl::cc::ConvolutionalEncoder ccEncoder;
    scl::cc::SoftViterbiDecoder ccDecoder;
    std::vector<s4ldpc::DirectGraph> ldpcGraphs;
};

const std::vector<SchemeSpec>& schemeSpecs();
std::string channelName(Channel channel);
double sigmaSquaredFromEsN0(double esN0Db);
double ebN0FromEsN0(double esN0Db, double actualRate);
double burstBeta(double isrDb);
std::vector<std::uint8_t> payloadForFrame(std::uint64_t frameIndex);
std::vector<std::complex<double>> complexNoise(std::uint64_t group,
                                               std::uint64_t frameIndex,
                                               std::size_t count);
std::vector<std::uint8_t> encodeFrame(CodecContext& context,
                                      Scheme scheme,
                                      const std::vector<std::uint8_t>& payload);
ChannelTrace runChannel(Channel channel,
                        const std::vector<std::uint8_t>& codeword,
                        double esN0Db,
                        std::uint64_t frameIndex,
                        bool addAwgn = true,
                        bool applyImpairment = true);
DecodeOutcome decodeFrame(CodecContext& context,
                          Scheme scheme,
                          const std::vector<double>& llr);
std::size_t bitErrors(const std::vector<std::uint8_t>& a,
                      const std::vector<std::uint8_t>& b);

}  // namespace s5
