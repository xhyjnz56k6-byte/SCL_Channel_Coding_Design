#ifndef SCL_BCH_SIMULATION_BCH_IMPAIRMENT_CHANNELS_HPP
#define SCL_BCH_SIMULATION_BCH_IMPAIRMENT_CHANNELS_HPP

#include "common/types.hpp"

#include <complex>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace scl::bch::simulation {

enum class StartPolicy {
    FrameStart,
    FrameMiddle,
    FrameEnd,
    SegmentInterior,
    OneBeforeSegmentBoundary,
    OnSegmentBoundary,
    UniformRandom
};

enum class CfoCompensationMode { None, Perfect };

struct ResidualCfoConfig {
    double initialPhaseDeg = 0.0;
    double frameRotationDeg = 0.0;
    double noiseVariance = 0.0;
    CfoCompensationMode compensationMode = CfoCompensationMode::None;
};

struct ResidualCfoOutput {
    std::vector<std::complex<double>> receivedSamples;
    std::vector<std::complex<double>> compensatedSamples;
    common::BitVector hardBits;
    double deltaPhiRad = 0.0;
};

struct BlockageConfig {
    double attenuationDb = 0.0;
    bool completeBlockage = false;
    std::size_t start = 0U;
    std::size_t length = 0U;
    double noiseVariance = 0.0;
};

struct BlockageOutput {
    common::RealVector receivedSamples;
    common::BitVector hardBits;
    double blockAmplitude = 1.0;
};

double degreesToRadians(double degrees);
ResidualCfoOutput applyResidualCfo(
    const common::RealVector& symbols,
    const common::RealVector& standardComplexNoise,
    const ResidualCfoConfig& config);
BlockageOutput applyShortBlockage(
    const common::RealVector& symbols,
    const common::RealVector& standardNoise,
    const BlockageConfig& config);
common::BitVector applyPostHardDecisionBurst(
    const common::BitVector& hardBits, std::size_t start, std::size_t length);

std::uint64_t deterministicDomainValue(
    std::uint64_t seed, std::uint64_t frameIndex, const std::string& domain);
std::size_t chooseStartIndex(
    StartPolicy policy,
    std::size_t frameLength,
    std::size_t impairmentLength,
    std::size_t segmentLength,
    std::uint64_t seed,
    std::uint64_t frameIndex,
    const std::string& domain);
StartPolicy parseStartPolicy(const std::string& value);
std::string startPolicyName(StartPolicy value);

}  // namespace scl::bch::simulation

#endif
