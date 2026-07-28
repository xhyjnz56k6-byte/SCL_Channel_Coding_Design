#include "stage07_multipath_validation_core.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace scl::bch::s2::stage07 {
namespace {

using Clock = std::chrono::steady_clock;

std::uint64_t elapsedNs(Clock::time_point start) {
    return static_cast<std::uint64_t>(
        std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now() - start).count());
}

void requireFinite(const std::vector<double>& values, const char* label) {
    for (double value : values) {
        if (!std::isfinite(value)) throw std::invalid_argument(std::string("non-finite ") + label);
    }
}

}  // namespace

double energy(const std::vector<double>& values) {
    double result = 0.0;
    for (double value : values) result += value * value;
    return result;
}

ChannelModel frozenChannel() {
    ChannelModel model;
    const double rawEnergy = energy(model.rawImpulse);
    if (!(rawEnergy > 0.0) || !std::isfinite(rawEnergy)) {
        throw std::logic_error("invalid frozen channel energy");
    }
    model.impulse = model.rawImpulse;
    const double scale = std::sqrt(rawEnergy);
    for (double& value : model.impulse) value /= scale;
    if (std::abs(energy(model.impulse) - 1.0) > 1e-14) {
        throw std::logic_error("frozen channel normalization failed");
    }
    return model;
}

std::vector<double> convolveFull(const std::vector<double>& symbols,
                                 const std::vector<double>& impulse) {
    if (symbols.empty() || impulse.empty()) throw std::invalid_argument("empty convolution input");
    requireFinite(symbols, "symbol");
    requireFinite(impulse, "impulse");
    std::vector<double> output(symbols.size() + impulse.size() - 1U, 0.0);
    for (std::size_t i = 0; i < symbols.size(); ++i) {
        for (std::size_t tap = 0; tap < impulse.size(); ++tap) {
            output[i + tap] += symbols[i] * impulse[tap];
        }
    }
    return output;
}

LinearMmse::LinearMmse(std::size_t symbolCount, std::vector<double> impulse, double sigma2)
    : symbolCount_(symbolCount), bandwidth_(impulse.empty() ? 0U : impulse.size() - 1U),
      impulse_(std::move(impulse)), sigma2_(sigma2) {
    if (symbolCount_ == 0U || impulse_.empty() || !std::isfinite(sigma2_) || sigma2_ < 0.0) {
        throw std::invalid_argument("invalid MMSE configuration");
    }
    requireFinite(impulse_, "impulse");
    if (std::abs(energy(impulse_) - 1.0) > 1e-12) {
        throw std::invalid_argument("MMSE impulse is not unit energy");
    }
    const std::size_t stride = bandwidth_ + 1U;
    normalBand_.assign(symbolCount_ * stride, 0.0);
    for (std::size_t row = 0; row < symbolCount_; ++row) {
        for (std::size_t delta = 0; delta <= std::min(row, bandwidth_); ++delta) {
            const std::size_t column = row - delta;
            double value = 0.0;
            for (std::size_t sample = row; sample < observationCount(); ++sample) {
                const std::size_t a = sample - row;
                const std::size_t b = sample - column;
                if (a < impulse_.size() && b < impulse_.size()) {
                    value += impulse_[a] * impulse_[b];
                }
            }
            normalBand_[row * stride + delta] = value;
        }
        normalBand_[row * stride] += sigma2_;
    }
    choleskyBand_.assign(normalBand_.size(), 0.0);
    for (std::size_t i = 0; i < symbolCount_; ++i) {
        const std::size_t firstJ = i > bandwidth_ ? i - bandwidth_ : 0U;
        for (std::size_t j = firstJ; j <= i; ++j) {
            double value = normalBand_[i * stride + (i - j)];
            const std::size_t firstK = std::max(
                i > bandwidth_ ? i - bandwidth_ : 0U,
                j > bandwidth_ ? j - bandwidth_ : 0U);
            for (std::size_t k = firstK; k < j; ++k) {
                value -= lower(i, k) * lower(j, k);
            }
            if (i == j) {
                if (!(value > 0.0) || !std::isfinite(value)) {
                    throw std::runtime_error("MMSE Cholesky is not positive definite");
                }
                choleskyBand_[i * stride] = std::sqrt(value);
            } else {
                choleskyBand_[i * stride + (i - j)] =
                    value / choleskyBand_[j * stride];
            }
        }
    }
}

double LinearMmse::lower(std::size_t row, std::size_t column) const {
    if (row < column || row - column > bandwidth_) return 0.0;
    return choleskyBand_[row * (bandwidth_ + 1U) + row - column];
}

EqualizedFrame LinearMmse::apply(const std::vector<double>& transmitted,
                                 const std::vector<double>& standardGaussian) const {
    if (transmitted.size() != symbolCount_ || standardGaussian.size() != observationCount()) {
        throw std::invalid_argument("MMSE frame dimension mismatch");
    }
    requireFinite(transmitted, "transmitted symbol");
    requireFinite(standardGaussian, "Gaussian sample");
    EqualizedFrame output;
    auto start = Clock::now();
    output.convolution = convolveFull(transmitted, impulse_);
    output.received.resize(observationCount());
    const double sigma = std::sqrt(sigma2_);
    for (std::size_t i = 0; i < observationCount(); ++i) {
        output.received[i] = output.convolution[i] + sigma * standardGaussian[i];
    }
    output.channelTimeNs = elapsedNs(start);

    start = Clock::now();
    output.rhs.assign(symbolCount_, 0.0);
    for (std::size_t i = 0; i < symbolCount_; ++i) {
        for (std::size_t tap = 0; tap < impulse_.size(); ++tap) {
            output.rhs[i] += impulse_[tap] * output.received[i + tap];
        }
    }
    std::vector<double> forward(symbolCount_, 0.0);
    for (std::size_t i = 0; i < symbolCount_; ++i) {
        double value = output.rhs[i];
        const std::size_t first = i > bandwidth_ ? i - bandwidth_ : 0U;
        for (std::size_t j = first; j < i; ++j) value -= lower(i, j) * forward[j];
        forward[i] = value / lower(i, i);
    }
    output.symbols.assign(symbolCount_, 0.0);
    for (std::size_t reverse = symbolCount_; reverse-- > 0U;) {
        double value = forward[reverse];
        const std::size_t last = std::min(symbolCount_ - 1U, reverse + bandwidth_);
        for (std::size_t row = reverse + 1U; row <= last; ++row) {
            value -= lower(row, reverse) * output.symbols[row];
        }
        output.symbols[reverse] = value / lower(reverse, reverse);
    }
    output.equalizeTimeNs = elapsedNs(start);
    output.hardBits.resize(symbolCount_);
    for (std::size_t i = 0; i < symbolCount_; ++i) {
        output.hardBits[i] = stage01::hardDecision(output.symbols[i]);
    }
    double residualSquared = 0.0;
    double rhsSquared = 0.0;
    const std::size_t stride = bandwidth_ + 1U;
    for (std::size_t row = 0; row < symbolCount_; ++row) {
        double ax = normalBand_[row * stride] * output.symbols[row];
        for (std::size_t delta = 1; delta <= bandwidth_; ++delta) {
            if (row >= delta) ax += normalBand_[row * stride + delta] * output.symbols[row - delta];
            if (row + delta < symbolCount_) {
                ax += normalBand_[(row + delta) * stride + delta] * output.symbols[row + delta];
            }
        }
        const double difference = ax - output.rhs[row];
        residualSquared += difference * difference;
        rhsSquared += output.rhs[row] * output.rhs[row];
    }
    output.residual = std::sqrt(residualSquared) / std::max(1.0, std::sqrt(rhsSquared));
    if (!std::isfinite(output.residual)) throw std::runtime_error("non-finite solver residual");
    return output;
}

std::size_t LinearMmse::observationCount() const {
    return symbolCount_ + impulse_.size() - 1U;
}
const std::vector<double>& LinearMmse::normalLowerBand() const { return normalBand_; }
double LinearMmse::sigma2() const { return sigma2_; }

std::size_t countErrors(const common::BitVector& a, const common::BitVector& b) {
    if (a.size() != b.size()) throw std::invalid_argument("bit vector length mismatch");
    std::size_t result = 0U;
    for (std::size_t i = 0; i < a.size(); ++i) result += a[i] != b[i];
    return result;
}

void addFrame(FrameCounts& counts, stage02::CaseId caseId,
              const common::BitVector& payload, double ebn0Db,
              std::uint64_t masterSeed, std::uint64_t ebn0Index,
              std::uint64_t frameIndex, bool noiseless) {
    const auto& contract = stage02::caseContract(caseId);
    if (payload.size() != contract.payloadLength) throw std::invalid_argument("payload length mismatch");
    auto start = Clock::now();
    const auto encoded = stage02::encodeFrame(caseId, payload);
    counts.encodeTimeTotalNs += elapsedNs(start);
    std::vector<double> symbols(encoded.encodedBits.size());
    for (std::size_t i = 0; i < symbols.size(); ++i) symbols[i] = stage01::bpsk(encoded.encodedBits[i]);
    const double sigma2 = noiseless ? 0.0 : stage01::awgnSigma2(contract.actualRate, ebn0Db);
    LinearMmse equalizer(symbols.size(), frozenChannel().impulse, sigma2);
    stage01::RandomIdentity identity{
        masterSeed, "stage07_multipath_validation:" + frozenChannel().id + ":P0",
        contract.caseId, ebn0Index, frameIndex};
    const auto noise = stage01::standardGaussianFrame(
        identity, stage01::RandomDomain::Awgn, equalizer.observationCount());
    const auto equalized = equalizer.apply(symbols, noise);
    start = Clock::now();
    const auto decoded = stage02::decodeFrame(caseId, equalized.hardBits);
    const std::uint64_t decodeNs = elapsedNs(start);
    const std::size_t errors = countErrors(payload, decoded.payload);
    ++counts.totalFrames;
    counts.totalPayloadBits += payload.size();
    counts.payloadErrorBits += errors;
    counts.payloadErrorFrames += errors != 0U;
    counts.decoderFailureFrames += !decoded.reportedSuccess;
    counts.miscorrectionFrames += decoded.reportedSuccess && errors != 0U;
    counts.undetectedErrorFrames += decoded.reportedSuccess && errors != 0U;
    counts.trueSuccessFrames += errors == 0U;
    counts.channelTimeTotalNs += equalized.channelTimeNs;
    counts.equalizeTimeTotalNs += equalized.equalizeTimeNs;
    counts.decodeTimeTotalNs += decodeNs;
    counts.decodeTimesNs.push_back(decodeNs);
    counts.equalizeTimesNs.push_back(equalized.equalizeTimeNs);
    counts.solverResidualSum += equalized.residual;
    counts.solverResidualMax = std::max(counts.solverResidualMax, equalized.residual);
}

std::uint64_t percentile(std::vector<std::uint64_t> values, double fraction) {
    if (values.empty()) return 0U;
    std::sort(values.begin(), values.end());
    const double position = fraction * static_cast<double>(values.size() - 1U);
    return values[static_cast<std::size_t>(std::llround(position))];
}

}  // namespace scl::bch::s2::stage07
