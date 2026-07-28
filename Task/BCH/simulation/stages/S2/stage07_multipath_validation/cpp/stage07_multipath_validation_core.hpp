#ifndef SCL_BCH_S2_STAGE07_MULTIPATH_VALIDATION_CORE_HPP
#define SCL_BCH_S2_STAGE07_MULTIPATH_VALIDATION_CORE_HPP

#include "stage01_foundation_awgn.hpp"
#include "stage02_case_contract.hpp"

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace scl::bch::s2::stage07 {

struct ChannelModel {
    std::string id = "S2_FIXED_REAL_FIR_V1";
    std::vector<double> rawImpulse{1.0, 0.65, 0.0, 0.35};
    std::vector<double> impulse;
};

struct EqualizedFrame {
    std::vector<double> convolution;
    std::vector<double> received;
    std::vector<double> rhs;
    std::vector<double> symbols;
    common::BitVector hardBits;
    double residual = 0.0;
    std::uint64_t channelTimeNs = 0U;
    std::uint64_t equalizeTimeNs = 0U;
};

struct FrameCounts {
    std::uint64_t totalFrames = 0U;
    std::uint64_t totalPayloadBits = 0U;
    std::uint64_t payloadErrorBits = 0U;
    std::uint64_t payloadErrorFrames = 0U;
    std::uint64_t decoderFailureFrames = 0U;
    std::uint64_t miscorrectionFrames = 0U;
    std::uint64_t undetectedErrorFrames = 0U;
    std::uint64_t trueSuccessFrames = 0U;
    std::uint64_t encodeTimeTotalNs = 0U;
    std::uint64_t channelTimeTotalNs = 0U;
    std::uint64_t equalizeTimeTotalNs = 0U;
    std::uint64_t decodeTimeTotalNs = 0U;
    std::vector<std::uint64_t> decodeTimesNs;
    std::vector<std::uint64_t> equalizeTimesNs;
    double solverResidualSum = 0.0;
    double solverResidualMax = 0.0;
};

ChannelModel frozenChannel();
double energy(const std::vector<double>& values);
std::vector<double> convolveFull(const std::vector<double>& symbols,
                                 const std::vector<double>& impulse);

class LinearMmse {
public:
    LinearMmse(std::size_t symbolCount, std::vector<double> impulse, double sigma2);
    EqualizedFrame apply(const std::vector<double>& transmitted,
                         const std::vector<double>& standardGaussian) const;
    std::size_t observationCount() const;
    const std::vector<double>& normalLowerBand() const;
    double sigma2() const;

private:
    double lower(std::size_t row, std::size_t column) const;
    std::size_t symbolCount_ = 0U;
    std::size_t bandwidth_ = 0U;
    std::vector<double> impulse_;
    double sigma2_ = 0.0;
    std::vector<double> normalBand_;
    std::vector<double> choleskyBand_;
};

std::size_t countErrors(const common::BitVector& a, const common::BitVector& b);
void addFrame(FrameCounts& counts, stage02::CaseId caseId,
              const common::BitVector& payload, double ebn0Db,
              std::uint64_t masterSeed, std::uint64_t ebn0Index,
              std::uint64_t frameIndex, bool noiseless = false);
std::uint64_t percentile(std::vector<std::uint64_t> values, double fraction);

}  // namespace scl::bch::s2::stage07

#endif
