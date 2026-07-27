#include "bch_simulation/bch_impairment_channels.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace scl::bch::simulation {
namespace {

void validateFinite(double value, const char* name) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(std::string(name) + " must be finite");
    }
}

void validateNoise(const common::RealVector& noise, std::size_t required) {
    if (noise.size() != required) {
        throw std::invalid_argument("standard-noise length mismatch");
    }
    for (double value : noise) validateFinite(value, "standard noise");
}

std::uint64_t mix64(std::uint64_t value) {
    value ^= value >> 30U;
    value *= 0xbf58476d1ce4e5b9ULL;
    value ^= value >> 27U;
    value *= 0x94d049bb133111ebULL;
    value ^= value >> 31U;
    return value;
}

}  // namespace

double degreesToRadians(double degrees) {
    validateFinite(degrees, "degrees");
    return degrees * 3.141592653589793238462643383279502884 / 180.0;
}

ResidualCfoOutput applyResidualCfo(
    const common::RealVector& symbols,
    const common::RealVector& standardComplexNoise,
    const ResidualCfoConfig& config) {
    if (symbols.size() < 2U) {
        throw std::invalid_argument("CFO frame must contain at least two symbols");
    }
    validateFinite(config.initialPhaseDeg, "initial phase");
    validateFinite(config.frameRotationDeg, "frame rotation");
    validateFinite(config.noiseVariance, "noise variance");
    if (config.noiseVariance < 0.0) {
        throw std::invalid_argument("noise variance must be nonnegative");
    }
    validateNoise(standardComplexNoise, symbols.size() * 2U);
    ResidualCfoOutput result;
    result.deltaPhiRad = degreesToRadians(config.frameRotationDeg) /
                         static_cast<double>(symbols.size() - 1U);
    const double phi0 = degreesToRadians(config.initialPhaseDeg);
    const double componentSigma = std::sqrt(config.noiseVariance / 2.0);
    result.receivedSamples.resize(symbols.size());
    result.compensatedSamples.resize(symbols.size());
    result.hardBits.resize(symbols.size());
    for (std::size_t index = 0U; index < symbols.size(); ++index) {
        validateFinite(symbols[index], "BPSK symbol");
        const double phase = phi0 + static_cast<double>(index) * result.deltaPhiRad;
        const std::complex<double> rotation(std::cos(phase), std::sin(phase));
        const std::complex<double> basebandSample(
            symbols[index] +
            componentSigma * standardComplexNoise[2U * index],
            componentSigma * standardComplexNoise[2U * index + 1U]);
        result.receivedSamples[index] = basebandSample * rotation;
        result.compensatedSamples[index] =
            config.compensationMode == CfoCompensationMode::Perfect
                ? result.receivedSamples[index] * std::conj(rotation)
                : result.receivedSamples[index];
        result.hardBits[index] =
            result.compensatedSamples[index].real() >= 0.0 ? 0U : 1U;
    }
    return result;
}

BlockageOutput applyShortBlockage(
    const common::RealVector& symbols,
    const common::RealVector& standardNoise,
    const BlockageConfig& config) {
    validateFinite(config.attenuationDb, "blockage attenuation");
    validateFinite(config.noiseVariance, "noise variance");
    if (config.noiseVariance < 0.0 || config.length == 0U ||
        config.start > symbols.size() ||
        config.length > symbols.size() - config.start) {
        throw std::invalid_argument("invalid blockage configuration");
    }
    validateNoise(standardNoise, symbols.size());
    BlockageOutput result;
    result.blockAmplitude =
        config.completeBlockage ? 0.0 : std::pow(10.0, config.attenuationDb / 20.0);
    const double sigma = std::sqrt(config.noiseVariance);
    result.receivedSamples.resize(symbols.size());
    result.hardBits.resize(symbols.size());
    for (std::size_t index = 0U; index < symbols.size(); ++index) {
        validateFinite(symbols[index], "BPSK symbol");
        const bool blocked = index >= config.start &&
                             index < config.start + config.length;
        const double amplitude = blocked ? result.blockAmplitude : 1.0;
        result.receivedSamples[index] = amplitude * symbols[index] +
                                        sigma * standardNoise[index];
        result.hardBits[index] = result.receivedSamples[index] >= 0.0 ? 0U : 1U;
    }
    return result;
}

common::BitVector applyPostHardDecisionBurst(
    const common::BitVector& hardBits, std::size_t start, std::size_t length) {
    common::validateBits(hardBits, "burst input");
    if (length == 0U || start > hardBits.size() ||
        length > hardBits.size() - start) {
        throw std::invalid_argument("invalid burst range");
    }
    common::BitVector result = hardBits;
    for (std::size_t index = start; index < start + length; ++index) {
        result[index] = static_cast<std::uint8_t>(1U - result[index]);
    }
    return result;
}

std::uint64_t deterministicDomainValue(
    std::uint64_t seed, std::uint64_t frameIndex, const std::string& domain) {
    if (domain.empty()) throw std::invalid_argument("domain separator is empty");
    std::uint64_t hash = 1469598103934665603ULL;
    for (unsigned char value : domain) {
        hash ^= static_cast<std::uint64_t>(value);
        hash *= 1099511628211ULL;
    }
    return mix64(hash ^ mix64(seed) ^ mix64(frameIndex + 0x9e3779b97f4a7c15ULL));
}

std::size_t chooseStartIndex(
    StartPolicy policy,
    std::size_t frameLength,
    std::size_t impairmentLength,
    std::size_t segmentLength,
    std::uint64_t seed,
    std::uint64_t frameIndex,
    const std::string& domain) {
    if (frameLength == 0U || impairmentLength == 0U ||
        impairmentLength > frameLength) {
        throw std::invalid_argument("invalid start-index dimensions");
    }
    const std::size_t maximum = frameLength - impairmentLength;
    switch (policy) {
        case StartPolicy::FrameStart: return 0U;
        case StartPolicy::FrameMiddle: return maximum / 2U;
        case StartPolicy::FrameEnd: return maximum;
        case StartPolicy::UniformRandom:
            return static_cast<std::size_t>(
                deterministicDomainValue(seed, frameIndex, domain) % (maximum + 1U));
        case StartPolicy::SegmentInterior:
        case StartPolicy::OneBeforeSegmentBoundary:
        case StartPolicy::OnSegmentBoundary:
            if (segmentLength == 0U || segmentLength >= frameLength) {
                throw std::invalid_argument("segment policy requires a valid segment length");
            }
            break;
    }
    std::size_t candidate = segmentLength;
    if (policy == StartPolicy::SegmentInterior) {
        candidate = std::max<std::size_t>(1U, segmentLength / 2U);
    } else if (policy == StartPolicy::OneBeforeSegmentBoundary) {
        candidate = segmentLength - 1U;
    }
    return std::min(candidate, maximum);
}

StartPolicy parseStartPolicy(const std::string& value) {
    if (value == "FRAME_START") return StartPolicy::FrameStart;
    if (value == "FRAME_MIDDLE") return StartPolicy::FrameMiddle;
    if (value == "FRAME_END") return StartPolicy::FrameEnd;
    if (value == "SEGMENT_INTERIOR") return StartPolicy::SegmentInterior;
    if (value == "ONE_BEFORE_SEGMENT_BOUNDARY") {
        return StartPolicy::OneBeforeSegmentBoundary;
    }
    if (value == "ON_SEGMENT_BOUNDARY") return StartPolicy::OnSegmentBoundary;
    if (value == "UNIFORM_RANDOM") return StartPolicy::UniformRandom;
    throw std::invalid_argument("unsupported start policy");
}

std::string startPolicyName(StartPolicy value) {
    switch (value) {
        case StartPolicy::FrameStart: return "FRAME_START";
        case StartPolicy::FrameMiddle: return "FRAME_MIDDLE";
        case StartPolicy::FrameEnd: return "FRAME_END";
        case StartPolicy::SegmentInterior: return "SEGMENT_INTERIOR";
        case StartPolicy::OneBeforeSegmentBoundary:
            return "ONE_BEFORE_SEGMENT_BOUNDARY";
        case StartPolicy::OnSegmentBoundary: return "ON_SEGMENT_BOUNDARY";
        case StartPolicy::UniformRandom: return "UNIFORM_RANDOM";
    }
    throw std::invalid_argument("unsupported start policy");
}

}  // namespace scl::bch::simulation
