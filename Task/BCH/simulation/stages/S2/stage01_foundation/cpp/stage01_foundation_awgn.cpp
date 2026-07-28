#include "stage01_foundation_awgn.hpp"

#include <cmath>
#include <limits>
#include <stdexcept>

namespace scl::bch::s2::stage01 {
namespace {

constexpr double kTwoPi = 6.283185307179586476925286766559;

std::uint64_t splitmix64(std::uint64_t value) {
    value += 0x9e3779b97f4a7c15ULL;
    value = (value ^ (value >> 30U)) * 0xbf58476d1ce4e5b9ULL;
    value = (value ^ (value >> 27U)) * 0x94d049bb133111ebULL;
    return value ^ (value >> 31U);
}

double openUnit(std::uint64_t word) {
    return static_cast<double>((word >> 11U) + 1ULL) / 9007199254740994.0;
}

void validateIdentity(const RandomIdentity& identity) {
    if (identity.stageId.empty() || identity.caseId.empty()) {
        throw std::invalid_argument("stageId and caseId must be non-empty");
    }
}

}  // namespace

std::uint64_t stableTextId(const std::string& text) {
    std::uint64_t value = 1469598103934665603ULL;
    for (unsigned char byte : text) {
        value ^= static_cast<std::uint64_t>(byte);
        value *= 1099511628211ULL;
    }
    return value;
}

std::uint64_t randomWord(const RandomIdentity& identity,
                         RandomDomain domain,
                         std::uint64_t symbolIndex,
                         std::uint64_t lane) {
    validateIdentity(identity);
    std::uint64_t value = splitmix64(identity.masterSeed ^ 0x53325f524e475f31ULL);
    value = splitmix64(value ^ stableTextId(identity.stageId) ^ 0x01ULL);
    value = splitmix64(value ^ stableTextId(identity.caseId) ^ 0x02ULL);
    value = splitmix64(value ^ identity.ebn0Index ^ 0x03ULL);
    value = splitmix64(value ^ identity.frameIndex ^ 0x04ULL);
    value = splitmix64(value ^ static_cast<std::uint64_t>(domain) ^ 0x05ULL);
    value = splitmix64(value ^ symbolIndex ^ 0x06ULL);
    return splitmix64(value ^ lane ^ 0x07ULL);
}

double standardGaussian(const RandomIdentity& identity,
                        RandomDomain domain,
                        std::uint64_t symbolIndex) {
    const double u1 = openUnit(randomWord(identity, domain, symbolIndex, 0U));
    const double u2 = openUnit(randomWord(identity, domain, symbolIndex, 1U));
    return std::sqrt(-2.0 * std::log(u1)) * std::cos(kTwoPi * u2);
}

std::vector<double> standardGaussianFrame(const RandomIdentity& identity,
                                          RandomDomain domain,
                                          std::size_t symbolCount) {
    if (symbolCount == 0U || symbolCount > 1000U) {
        throw std::invalid_argument("symbolCount outside 1..1000");
    }
    std::vector<double> values(symbolCount);
    for (std::size_t i = 0; i < symbolCount; ++i) {
        values[i] = standardGaussian(identity, domain, i);
    }
    return values;
}

std::vector<unsigned> payloadFrame(const RandomIdentity& identity,
                                   std::size_t payloadLength) {
    if (payloadLength == 0U || payloadLength > 1000U) {
        throw std::invalid_argument("payloadLength outside 1..1000");
    }
    std::vector<unsigned> bits(payloadLength);
    for (std::size_t i = 0; i < payloadLength; ++i) {
        bits[i] = static_cast<unsigned>(randomWord(identity, RandomDomain::Payload, i, 0U) & 1ULL);
    }
    return bits;
}

double actualRate(std::size_t payloadLength, std::size_t encodedLength) {
    if (payloadLength == 0U || encodedLength == 0U || payloadLength > encodedLength) {
        throw std::invalid_argument("invalid payload/encoded lengths");
    }
    return static_cast<double>(payloadLength) / static_cast<double>(encodedLength);
}

double awgnSigma2(double rate, double ebn0DbValue) {
    if (!std::isfinite(rate) || rate <= 0.0 || rate > 1.0 || !std::isfinite(ebn0DbValue)) {
        throw std::invalid_argument("invalid AWGN parameters");
    }
    return 1.0 / (2.0 * rate * std::pow(10.0, ebn0DbValue / 10.0));
}

double snrLinear(double rate, double ebn0DbValue) {
    return 1.0 / awgnSigma2(rate, ebn0DbValue);
}

double snrDb(double rate, double ebn0DbValue) {
    static_cast<void>(awgnSigma2(rate, ebn0DbValue));
    return ebn0DbValue + 10.0 * std::log10(2.0 * rate);
}

double bpsk(unsigned bit) {
    if (bit > 1U) throw std::invalid_argument("BPSK bit must be binary");
    return bit == 0U ? 1.0 : -1.0;
}

unsigned hardDecision(double received) {
    if (!std::isfinite(received)) throw std::invalid_argument("hard decision input must be finite");
    return received < 0.0 ? 1U : 0U;
}

AwgnSample evaluateSample(double rate, double ebn0DbValue, double z, unsigned bit) {
    if (!std::isfinite(z)) throw std::invalid_argument("standard Gaussian sample must be finite");
    AwgnSample value;
    value.actualRate = rate;
    value.ebn0Db = ebn0DbValue;
    value.sigma2 = awgnSigma2(rate, ebn0DbValue);
    value.sigma = std::sqrt(value.sigma2);
    value.standardGaussian = z;
    value.noise = value.sigma * z;
    value.transmitted = bpsk(bit);
    value.received = value.transmitted + value.noise;
    value.hardDecision = hardDecision(value.received);
    value.snrLinear = snrLinear(rate, ebn0DbValue);
    value.snrDb = snrDb(rate, ebn0DbValue);
    return value;
}

const char* conversionFormula() {
    return "SNR_dB = EbN0_dB + 10*log10(2*R)";
}

}  // namespace scl::bch::s2::stage01
