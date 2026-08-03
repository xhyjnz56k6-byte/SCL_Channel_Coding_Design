#include "s5_comparison/s5.hpp"

#include "cc/block_encoder.hpp"
#include "cc/puncturing.hpp"
#include "cc/soft_viterbi.hpp"
#include "cc/trellis.hpp"
#include "common/frame_pool.hpp"
#include "common/gaussian_noise.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace s5 {
namespace {

using Clock = std::chrono::steady_clock;

double elapsedUs(Clock::time_point begin, Clock::time_point end) {
    return std::chrono::duration<double, std::micro>(end - begin).count();
}

constexpr double kPi = 3.141592653589793238462643383279502884;
constexpr std::uint64_t kAwgnGroup = 0x53354157474e0001ULL;
constexpr std::uint64_t kBurstGroup = 0x5335425552535401ULL;
constexpr std::uint64_t kStateGroup = 0x5335535441544501ULL;

const SchemeSpec& spec(Scheme scheme) {
    for (const auto& item : schemeSpecs()) if (item.scheme == scheme) return item;
    throw std::invalid_argument("unknown S5 scheme");
}

std::vector<std::uint8_t> asBytes(const scl::common::BitVector& input) {
    return std::vector<std::uint8_t>(input.begin(), input.end());
}

double finiteSoft(double value) {
    if (value > 0.0) return kNoiselessSoftMagnitude;
    if (value < 0.0) return -kNoiselessSoftMagnitude;
    return 0.0;
}

double stateUniform(std::uint64_t frameIndex, std::uint64_t channelTag) {
    std::uint64_t value = kNoiseSeed ^ kStateGroup ^ channelTag;
    value ^= frameIndex * 0x9e3779b97f4a7c15ULL;
    const std::uint64_t word = scl::common::splitmix64(value);
    return (static_cast<double>(word >> 11U) + 0.5) / 9007199254740992.0;
}

std::vector<double> solveCholesky(const std::vector<double>& lower,
                                  const std::vector<double>& rhs,
                                  std::size_t n) {
    std::vector<double> y(n, 0.0), x(n, 0.0);
    for (std::size_t i = 0; i < n; ++i) {
        double value = rhs[i];
        for (std::size_t j = 0; j < i; ++j) value -= lower[i * n + j] * y[j];
        y[i] = value / lower[i * n + i];
    }
    for (std::size_t ii = n; ii-- > 0;) {
        double value = y[ii];
        for (std::size_t j = ii + 1; j < n; ++j) value -= lower[j * n + ii] * x[j];
        x[ii] = value / lower[ii * n + ii];
    }
    return x;
}

void multipathReceiver(const std::vector<std::complex<double>>& rx,
                       std::size_t n,
                       double sigmaSquared,
                       ChannelTrace& trace) {
    struct MmseCache {
        std::size_t n = 0;
        double sigmaSquared = 0.0;
        std::vector<double> lower;
        std::vector<double> gain;
        std::vector<double> variance;
    };
    static std::vector<MmseCache> caches;
    const double norm = std::sqrt(1.0 + 0.65 * 0.65 + 0.35 * 0.35);
    const double taps[3] = {1.0 / norm, 0.65 / norm, 0.35 / norm};
    const int delays[3] = {0, 1, 3};
    const auto projectionBegin = Clock::now();
    std::vector<double> rhs(n, 0.0);
    for (std::size_t col = 0; col < n; ++col) {
        for (int a = 0; a < 3; ++a) {
            const std::size_t row = col + static_cast<std::size_t>(delays[a]);
            rhs[col] += taps[a] * rx[row].real();
        }
    }
    trace.projectionTimeUs += elapsedUs(projectionBegin, Clock::now());
    auto found = std::find_if(caches.begin(), caches.end(), [n, sigmaSquared](const MmseCache& item) {
        return item.n == n && item.sigmaSquared == sigmaSquared;
    });
    if (found == caches.end()) {
        MmseCache cache;
        cache.n = n;
        cache.sigmaSquared = sigmaSquared;
        std::vector<double> b(n * n, 0.0);
        for (std::size_t col = 0; col < n; ++col) {
            for (int a = 0; a < 3; ++a) {
                const std::size_t row = col + static_cast<std::size_t>(delays[a]);
                for (int c = 0; c < 3; ++c) {
                    const int other = static_cast<int>(row) - delays[c];
                    if (other >= 0 && other < static_cast<int>(n))
                        b[col * n + static_cast<std::size_t>(other)] += taps[a] * taps[c];
                }
            }
            b[col * n + col] += sigmaSquared;
        }
        cache.lower.assign(n * n, 0.0);
        for (std::size_t i = 0; i < n; ++i) {
            for (std::size_t j = 0; j <= i; ++j) {
                double value = b[i * n + j];
                for (std::size_t k = 0; k < j; ++k) value -= cache.lower[i * n + k] * cache.lower[j * n + k];
                if (i == j) {
                    if (!(value > 0.0)) throw std::runtime_error("multipath MMSE matrix is not positive definite");
                    cache.lower[i * n + j] = std::sqrt(value);
                } else cache.lower[i * n + j] = value / cache.lower[j * n + j];
            }
        }
        cache.gain.assign(n, 1.0);
        cache.variance.assign(n, 0.0);
        if (sigmaSquared > 0.0) {
            std::vector<double> unit(n, 0.0);
            for (std::size_t i = 0; i < n; ++i) {
                std::fill(unit.begin(), unit.end(), 0.0);
                unit[i] = 1.0;
                const auto column = solveCholesky(cache.lower, unit, n);
                const double cii = column[i];
                cache.gain[i] = 1.0 - sigmaSquared * cii;
                cache.variance[i] = sigmaSquared * cii * cache.gain[i];
                if (!(cache.gain[i] > 0.0) || !(cache.variance[i] > 0.0) || !std::isfinite(cache.variance[i]))
                    throw std::runtime_error("invalid multipath gk/vk");
            }
        }
        caches.push_back(std::move(cache));
        found = std::prev(caches.end());
    }
    const auto equalizationBegin = Clock::now();
    trace.equalized = solveCholesky(found->lower, rhs, n);
    trace.gain = found->gain;
    trace.variance = found->variance;
    trace.equalizationTimeUs += elapsedUs(equalizationBegin, Clock::now());
    const auto llrBegin = Clock::now();
    trace.llr.assign(n, 0.0);
    if (sigmaSquared == 0.0)
        for (std::size_t i = 0; i < n; ++i) trace.llr[i] = finiteSoft(trace.equalized[i]);
    else
        for (std::size_t i = 0; i < n; ++i) trace.llr[i] = 2.0 * trace.gain[i] * trace.equalized[i] / trace.variance[i];
    trace.llrGenerationTimeUs += elapsedUs(llrBegin, Clock::now());
}

}  // namespace

const std::vector<SchemeSpec>& schemeSpecs() {
    static const std::vector<SchemeSpec> values = {
        {Scheme::CcR23, "CC_R23_BLOCK_FLOAT", "RATE_NEAR_2_3", 459, 300.0 / 459.0, 0.0},
        {Scheme::CcR12, "CC_R12_BLOCK_FLOAT", "RATE_NEAR_1_2", 612, 300.0 / 612.0, 0.0},
        {Scheme::LdpcN480, "LDPC_BG2_N480_NMS", "RATE_NEAR_2_3", 480, 300.0 / 480.0, 0.95},
        {Scheme::LdpcN640, "LDPC_BG2_N640_NMS", "RATE_NEAR_1_2", 640, 300.0 / 640.0, 0.80}
    };
    return values;
}

CodecContext::CodecContext()
    : ccTrellis(), ccEncoder(ccTrellis), ccDecoder(ccTrellis) {
    for (const auto& item : s4ldpc::freezeS4Cases()) {
        if (item.actualLength == 480 || item.actualLength == 640) {
            ldpcGraphs.push_back(s4ldpc::buildDirectGraph(item));
        }
    }
    if (ldpcGraphs.size() != 2) throw std::runtime_error("failed to cache two frozen S5 LDPC graphs");
}

std::string channelName(Channel channel) {
    switch (channel) {
        case Channel::Awgn: return "AWGN";
        case Channel::Multipath: return "FIXED_MULTIPATH_REAL_MMSE";
        case Channel::Cfo: return "CFO_30_DEG";
        case Channel::Doppler: return "LINEAR_TIME_VARYING_FREQUENCY";
        case Channel::Blockage10: return "KNOWN_BLOCKAGE_10_PERCENT";
        case Channel::Blockage5: return "KNOWN_BLOCKAGE_5_PERCENT";
        case Channel::Burst: return "UNKNOWN_BURST_5_PERCENT_ISR_10DB";
    }
    throw std::invalid_argument("unknown channel");
}

double sigmaSquaredFromEsN0(double esN0Db) {
    if (!std::isfinite(esN0Db)) throw std::invalid_argument("Es/N0 must be finite");
    return 1.0 / (2.0 * std::pow(10.0, esN0Db / 10.0));
}

double ebN0FromEsN0(double esN0Db, double actualRate) {
    if (!(actualRate > 0.0 && actualRate <= 1.0)) throw std::invalid_argument("actualRate outside (0,1]");
    return esN0Db - 10.0 * std::log10(actualRate);
}

double burstBeta(double isrDb) {
    if (!std::isfinite(isrDb)) throw std::invalid_argument("ISR must be finite");
    return std::sqrt(std::pow(10.0, isrDb / 10.0) / 2.0);
}

std::vector<std::uint8_t> payloadForFrame(std::uint64_t frameIndex) {
    return asBytes(scl::common::generatePayloadBits(kPayloadSeed, kPayloadLength, frameIndex));
}

std::vector<std::complex<double>> complexNoise(std::uint64_t group,
                                               std::uint64_t frameIndex,
                                               std::size_t count) {
    std::vector<std::complex<double>> result(count);
    for (std::size_t i = 0; i < count; ++i) {
        scl::common::NoiseKey realKey{kNoiseSeed, group, frameIndex, 2U * i, kNoisePolicyVersion};
        scl::common::NoiseKey imagKey{kNoiseSeed, group, frameIndex, 2U * i + 1U, kNoisePolicyVersion};
        result[i] = {scl::common::standardGaussianSample(realKey),
                     scl::common::standardGaussianSample(imagKey)};
    }
    return result;
}

std::vector<std::uint8_t> encodeFrame(CodecContext& context,
                                      Scheme scheme,
                                      const std::vector<std::uint8_t>& payload) {
    if (payload.size() != kPayloadLength) throw std::invalid_argument("payload length must be 300");
    if (scheme == Scheme::CcR12 || scheme == Scheme::CcR23) {
        const auto encoded = context.ccEncoder.encode_block(payload, true, 0);
        if (scheme == Scheme::CcR12) return encoded.mother_bits;
        return scl::cc::puncture_bits(encoded.mother_bits, {"R23_1101", {1, 1, 0, 1}}).bits;
    }
    const int target = scheme == Scheme::LdpcN480 ? 480 : 640;
    for (const auto& graph : context.ldpcGraphs) {
        if (graph.config.actualLength == target) return s4ldpc::encode(graph, payload);
    }
    throw std::runtime_error("frozen LDPC graph not found");
}

ChannelTrace runChannel(Channel channel,
                        const std::vector<std::uint8_t>& codeword,
                        double esN0Db,
                        std::uint64_t frameIndex,
                        bool addAwgn,
                        bool applyImpairment) {
    if (codeword.empty()) throw std::invalid_argument("empty codeword");
    const std::size_t n = codeword.size();
    ChannelTrace trace;
    trace.tx.resize(n);
    for (std::size_t i = 0; i < n; ++i) trace.tx[i] = {codeword[i] ? -1.0 : 1.0, 0.0};
    trace.sigmaSquared = addAwgn ? sigmaSquaredFromEsN0(esN0Db) : 0.0;
    trace.impaired = trace.tx;

    const auto impairmentBegin = Clock::now();
    if (applyImpairment && channel == Channel::Multipath) {
        const double norm = std::sqrt(1.0 + 0.65 * 0.65 + 0.35 * 0.35);
        const double taps[3] = {1.0 / norm, 0.65 / norm, 0.35 / norm};
        const int delays[3] = {0, 1, 3};
        trace.impaired.assign(n + 3, {0.0, 0.0});
        for (std::size_t i = 0; i < n; ++i) for (int p = 0; p < 3; ++p) {
            trace.impaired[i + static_cast<std::size_t>(delays[p])] += taps[p] * trace.tx[i];
        }
    } else if (applyImpairment && channel == Channel::Cfo) {
        trace.phase.resize(n);
        for (std::size_t i = 0; i < n; ++i) {
            const double phase = n == 1 ? 0.0 : (kPi / 6.0) * static_cast<double>(i) / static_cast<double>(n - 1);
            trace.phase[i] = phase;
            trace.impaired[i] *= std::polar(1.0, phase);
        }
    } else if (applyImpairment && channel == Channel::Doppler) {
        trace.phase.assign(n, 0.0);
        trace.epsilon.assign(n, 0.0);
        const double span = n == 1 ? 0.0 : 2.0 / (3.0 * static_cast<double>(n - 1));
        for (std::size_t i = 0; i < n; ++i) {
            trace.epsilon[i] = span * (static_cast<double>(i) / static_cast<double>(n - 1) - 0.5);
            if (i > 0) trace.phase[i] = trace.phase[i - 1] + 2.0 * kPi * trace.epsilon[i - 1];
            trace.impaired[i] *= std::polar(1.0, trace.phase[i]);
        }
    } else if (applyImpairment && (channel == Channel::Blockage10 || channel == Channel::Blockage5)) {
        const double fraction = channel == Channel::Blockage10 ? 0.10 : 0.05;
        trace.damageLength = static_cast<std::size_t>(std::llround(fraction * static_cast<double>(n)));
        trace.relativeStart = stateUniform(frameIndex, 0x424c4f434bULL);
        trace.damageStart = static_cast<std::size_t>(std::floor(trace.relativeStart * (n - trace.damageLength + 1)));
        trace.mask.assign(n, 1.0);
        for (std::size_t i = 0; i < trace.damageLength; ++i) {
            trace.mask[trace.damageStart + i] = 0.0;
            trace.impaired[trace.damageStart + i] = {0.0, 0.0};
        }
    } else if (applyImpairment && channel == Channel::Burst) {
        trace.damageLength = static_cast<std::size_t>(std::llround(0.05 * static_cast<double>(n)));
        trace.relativeStart = stateUniform(frameIndex, 0x4255525354ULL);
        trace.damageStart = static_cast<std::size_t>(std::floor(trace.relativeStart * (n - trace.damageLength + 1)));
        trace.mask.assign(n, 0.0);
        const auto interference = complexNoise(kBurstGroup, frameIndex, n);
        const double beta = burstBeta(10.0);
        for (std::size_t i = 0; i < trace.damageLength; ++i) {
            const std::size_t k = trace.damageStart + i;
            trace.mask[k] = 1.0;
            trace.impaired[k] += beta * interference[k];
        }
    }
    trace.channelImpairmentTimeUs = elapsedUs(impairmentBegin, Clock::now());

    trace.rx = trace.impaired;
    const auto awgnBegin = Clock::now();
    if (addAwgn) {
        const auto noise = complexNoise(kAwgnGroup, frameIndex, trace.rx.size());
        const double sigma = std::sqrt(trace.sigmaSquared);
        for (std::size_t i = 0; i < trace.rx.size(); ++i) trace.rx[i] += sigma * noise[i];
    }
    trace.awgnTimeUs = elapsedUs(awgnBegin, Clock::now());
    if (channel == Channel::Multipath && applyImpairment) {
        multipathReceiver(trace.rx, n, trace.sigmaSquared, trace);
        trace.channelProcessingTimeUs = trace.channelImpairmentTimeUs + trace.awgnTimeUs
            + trace.equalizationTimeUs + trace.projectionTimeUs + trace.llrGenerationTimeUs;
        return trace;
    }
    const auto projectionBegin = Clock::now();
    std::vector<double> projected(n, 0.0);
    for (std::size_t i = 0; i < n; ++i) projected[i] = trace.rx[i].real();
    trace.projectionTimeUs = elapsedUs(projectionBegin, Clock::now());
    const auto llrBegin = Clock::now();
    trace.llr.resize(n);
    for (std::size_t i = 0; i < n; ++i) {
        if ((channel == Channel::Blockage10 || channel == Channel::Blockage5)
            && applyImpairment && trace.mask[i] == 0.0) trace.llr[i] = 0.0;
        else if (trace.sigmaSquared == 0.0) trace.llr[i] = finiteSoft(projected[i]);
        else trace.llr[i] = 2.0 * projected[i] / trace.sigmaSquared;
    }
    trace.llrGenerationTimeUs = elapsedUs(llrBegin, Clock::now());
    trace.channelProcessingTimeUs = trace.channelImpairmentTimeUs + trace.awgnTimeUs
        + trace.equalizationTimeUs + trace.projectionTimeUs + trace.llrGenerationTimeUs;
    return trace;
}

DecodeOutcome decodeFrame(CodecContext& context,
                          Scheme scheme,
                          const std::vector<double>& llr) {
    DecodeOutcome outcome;
    if (scheme == Scheme::CcR12 || scheme == Scheme::CcR23) {
        if (scheme == Scheme::CcR12) {
            if (llr.size() != 612) throw std::invalid_argument("R12 LLR length mismatch");
            std::vector<double> symbols(llr.size());
            std::transform(llr.begin(), llr.end(), symbols.begin(), [](double x) { return x * 0.5; });
            outcome.payload = context.ccDecoder.decode_terminated_symbols(symbols, 306, 6, 0, 0).payload_bits;
        } else {
            if (llr.size() != 459) throw std::invalid_argument("R23 LLR length mismatch");
            std::vector<double> symbols(llr.size());
            std::transform(llr.begin(), llr.end(), symbols.begin(), [](double x) { return x * 0.5; });
            const auto expanded = scl::cc::depuncture_soft(symbols, 612, {"R23_1101", {1, 1, 0, 1}});
            outcome.payload = context.ccDecoder.decode_terminated_masked_symbols(
                expanded.expanded_values, expanded.observed_mask, 306, 6, 0, 0).payload_bits;
        }
        return outcome;
    }
    const auto& wanted = spec(scheme);
    for (const auto& graph : context.ldpcGraphs) if (graph.config.actualLength == static_cast<int>(wanted.transmittedLength)) {
        const auto decoded = s4ldpc::decodeLayeredNms(graph, llr, 32, wanted.ldpcAlpha);
        outcome.payload.assign(decoded.bits.begin(), decoded.bits.begin() + kPayloadLength);
        outcome.decoderFailure = !decoded.syndromePass;
        outcome.usedIterations = decoded.usedIterations;
        outcome.finalSyndromeWeight = decoded.finalSyndromeWeight;
        return outcome;
    }
    throw std::runtime_error("frozen LDPC graph not found");
}

std::size_t bitErrors(const std::vector<std::uint8_t>& a,
                      const std::vector<std::uint8_t>& b) {
    if (a.size() != b.size()) throw std::invalid_argument("bit vector length mismatch");
    std::size_t count = 0;
    for (std::size_t i = 0; i < a.size(); ++i) count += a[i] != b[i];
    return count;
}

}  // namespace s5
