#include "bch_simulation/fixed_multipath_mmse.hpp"

#include "common/demodulation.hpp"
#include "common/gaussian_noise.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace scl::bch::simulation {
namespace {

void validateConfig(const MultipathChannelConfig& config) {
    if (config.rawTaps.empty() || config.rawTaps.size() != config.delays.size()) {
        throw std::invalid_argument("multipath taps and delays must have equal nonzero size");
    }
    if (!config.receiverKnowsChannel || config.mmse.equalizerType != "KNOWN_CHANNEL_LINEAR_MMSE") {
        throw std::invalid_argument("S2 requires a known-channel linear MMSE receiver");
    }
    for (std::size_t i = 0; i < config.delays.size(); ++i) {
        if (!std::isfinite(config.rawTaps[i])) throw std::invalid_argument("non-finite multipath tap");
        if (i > 0U && config.delays[i] <= config.delays[i - 1U]) {
            throw std::invalid_argument("multipath delays must be strictly increasing");
        }
    }
}

std::vector<double> normalized(const MultipathChannelConfig& config) {
    validateConfig(config);
    std::vector<double> taps = config.rawTaps;
    const double energy = channelEnergy(taps);
    if (!(energy > 0.0) || !std::isfinite(energy)) throw std::invalid_argument("invalid channel energy");
    if (config.normalizeToUnitEnergy) {
        const double scale = std::sqrt(energy);
        for (double& tap : taps) tap /= scale;
    }
    return taps;
}

double lowerValue(const std::vector<std::vector<double>>& band,
                  std::size_t row, std::size_t column) {
    if (row < column || row - column >= band[row].size()) return 0.0;
    return band[row][row - column];
}

}  // namespace

MultipathChannelConfig frozenFixedMultipathConfig() {
    MultipathChannelConfig config;
    config.normalizedTaps = normalized(config);
    return config;
}

double channelEnergy(const std::vector<double>& taps) {
    double value = 0.0;
    for (double tap : taps) value += tap * tap;
    return value;
}

FixedMultipathMmseEqualizer::FixedMultipathMmseEqualizer(
    std::size_t symbolCount, const MultipathChannelConfig& channelConfig, double noiseVariance)
    : symbolCount_(symbolCount), config_(channelConfig), noiseVariance_(noiseVariance) {
    if (symbolCount_ == 0U || !std::isfinite(noiseVariance_) || noiseVariance_ < 0.0) {
        throw std::invalid_argument("invalid MMSE dimensions or noise variance");
    }
    config_.normalizedTaps = normalized(config_);
    maximumDelay_ = config_.delays.back();
    bandwidth_ = maximumDelay_;
    const auto setupStart = std::chrono::steady_clock::now();

    std::vector<std::vector<double>> normal(
        symbolCount_, std::vector<double>(bandwidth_ + 1U, 0.0));
    for (std::size_t column = 0; column < symbolCount_; ++column) {
        for (std::size_t a = 0; a < config_.normalizedTaps.size(); ++a) {
            const std::size_t row = column + config_.delays[a];
            for (std::size_t b = 0; b < config_.normalizedTaps.size(); ++b) {
                if (row < config_.delays[b]) continue;
                const std::size_t otherColumn = row - config_.delays[b];
                if (otherColumn >= symbolCount_ || column < otherColumn ||
                    column - otherColumn > bandwidth_) continue;
                normal[column][column - otherColumn] +=
                    config_.normalizedTaps[a] * config_.normalizedTaps[b];
            }
        }
    }
    for (std::size_t i = 0; i < symbolCount_; ++i) normal[i][0] += noiseVariance_;

    choleskyLowerBand_.assign(
        symbolCount_, std::vector<double>(bandwidth_ + 1U, 0.0));
    for (std::size_t i = 0; i < symbolCount_; ++i) {
        const std::size_t firstColumn = i > bandwidth_ ? i - bandwidth_ : 0U;
        for (std::size_t j = firstColumn; j <= i; ++j) {
            double value = normal[i][i - j];
            const std::size_t firstK = std::max(
                i > bandwidth_ ? i - bandwidth_ : 0U,
                j > bandwidth_ ? j - bandwidth_ : 0U);
            for (std::size_t k = firstK; k < j; ++k) {
                value -= lowerValue(choleskyLowerBand_, i, k) *
                         lowerValue(choleskyLowerBand_, j, k);
            }
            if (i == j) {
                if (!(value > 0.0) || !std::isfinite(value)) {
                    throw std::runtime_error("MMSE Cholesky factorization is not positive definite");
                }
                choleskyLowerBand_[i][0] = std::sqrt(value);
            } else {
                choleskyLowerBand_[i][i - j] =
                    value / choleskyLowerBand_[j][0];
            }
        }
    }
    setupTimeUs_ = std::chrono::duration<double, std::micro>(
        std::chrono::steady_clock::now() - setupStart).count();
}

ChannelOutput FixedMultipathMmseEqualizer::apply(
    const std::vector<double>& transmittedSymbols,
    const std::vector<double>& standardGaussianNoise) const {
    if (transmittedSymbols.size() != symbolCount_ ||
        standardGaussianNoise.size() != observationCount()) {
        throw std::invalid_argument("MMSE input length mismatch");
    }
    ChannelOutput output;
    output.fullConvolutionOutput.assign(observationCount(), 0.0);
    output.receivedSamples.assign(observationCount(), 0.0);
    output.standardGaussianNoise = standardGaussianNoise;
    for (std::size_t i = 0; i < symbolCount_; ++i) {
        if (!std::isfinite(transmittedSymbols[i])) throw std::invalid_argument("non-finite transmitted symbol");
        for (std::size_t tap = 0; tap < config_.normalizedTaps.size(); ++tap) {
            output.fullConvolutionOutput[i + config_.delays[tap]] +=
                config_.normalizedTaps[tap] * transmittedSymbols[i];
        }
    }
    const double sigma = std::sqrt(noiseVariance_);
    for (std::size_t i = 0; i < observationCount(); ++i) {
        if (!std::isfinite(standardGaussianNoise[i])) throw std::invalid_argument("non-finite Gaussian sample");
        output.receivedSamples[i] =
            output.fullConvolutionOutput[i] + sigma * standardGaussianNoise[i];
    }
    std::vector<double> pre(symbolCount_);
    std::copy_n(output.receivedSamples.begin(), symbolCount_, pre.begin());
    output.preEqualizationHardBits = common::hardDecision(pre);

    const auto equalizationStart = std::chrono::steady_clock::now();
    std::vector<double> rhs(symbolCount_, 0.0);
    for (std::size_t i = 0; i < symbolCount_; ++i) {
        for (std::size_t tap = 0; tap < config_.normalizedTaps.size(); ++tap) {
            rhs[i] += config_.normalizedTaps[tap] *
                      output.receivedSamples[i + config_.delays[tap]];
        }
    }
    std::vector<double> forward(symbolCount_, 0.0);
    for (std::size_t i = 0; i < symbolCount_; ++i) {
        double value = rhs[i];
        const std::size_t first = i > bandwidth_ ? i - bandwidth_ : 0U;
        for (std::size_t j = first; j < i; ++j) {
            value -= lowerValue(choleskyLowerBand_, i, j) * forward[j];
        }
        forward[i] = value / choleskyLowerBand_[i][0];
    }
    output.equalizedSymbols.assign(symbolCount_, 0.0);
    for (std::size_t reverse = symbolCount_; reverse-- > 0U;) {
        double value = forward[reverse];
        const std::size_t last = std::min(symbolCount_ - 1U, reverse + bandwidth_);
        for (std::size_t row = reverse + 1U; row <= last; ++row) {
            value -= lowerValue(choleskyLowerBand_, row, reverse) *
                     output.equalizedSymbols[row];
        }
        output.equalizedSymbols[reverse] =
            value / choleskyLowerBand_[reverse][0];
    }
    output.equalizationTimeUs = std::chrono::duration<double, std::micro>(
        std::chrono::steady_clock::now() - equalizationStart).count();
    output.hardBits = common::hardDecision(output.equalizedSymbols);
    output.diagnostics.channelEnergy = channelEnergy(config_.normalizedTaps);
    output.diagnostics.noiseVariance = noiseVariance_;
    output.diagnostics.transmittedLength = symbolCount_;
    output.diagnostics.observationLength = observationCount();
    output.diagnostics.equalizerMethod = "BANDED_CHOLESKY_NORMAL_EQUATIONS";
    return output;
}

std::size_t FixedMultipathMmseEqualizer::symbolCount() const { return symbolCount_; }
std::size_t FixedMultipathMmseEqualizer::observationCount() const {
    return symbolCount_ + maximumDelay_;
}
double FixedMultipathMmseEqualizer::setupTimeUs() const { return setupTimeUs_; }

ChannelOutput applyFixedMultipathMmse(
    const std::vector<double>& transmittedSymbols,
    const MultipathChannelConfig& channelConfig,
    double noiseVariance,
    const ChannelKey& key) {
    FixedMultipathMmseEqualizer equalizer(
        transmittedSymbols.size(), channelConfig, noiseVariance);
    const auto noise = common::generateStandardGaussianFrame(
        key.globalSeed, key.noiseGroup, key.frameIndex,
        equalizer.observationCount(), key.noisePolicyVersion);
    return equalizer.apply(transmittedSymbols, noise);
}

}  // namespace scl::bch::simulation
