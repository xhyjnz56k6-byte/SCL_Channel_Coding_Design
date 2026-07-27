#include "stage01_foundation_awgn.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

bool different(const std::vector<double>& left, const std::vector<double>& right) {
    return left.size() != right.size() || !std::equal(left.begin(), left.end(), right.begin());
}

}  // namespace

int main() {
    try {
        using namespace scl::bch::s2::stage01;
        const double rate = actualRate(200U, 285U);
        const double ebn0 = 3.25;
        const double expectedSigma2 = 1.0 / (2.0 * rate * std::pow(10.0, ebn0 / 10.0));
        require(std::abs(awgnSigma2(rate, ebn0) - expectedSigma2) < 1e-15, "sigma2 mismatch");
        require(std::abs(snrLinear(rate, ebn0) - 1.0 / expectedSigma2) < 1e-14, "snr linear mismatch");
        require(std::abs(snrDb(rate, ebn0) - (ebn0 + 10.0 * std::log10(2.0 * rate))) < 1e-14,
                "snr dB mismatch");
        require(bpsk(0U) == 1.0 && bpsk(1U) == -1.0, "BPSK mapping mismatch");
        require(hardDecision(0.0) == 0U && hardDecision(-1e-9) == 1U, "hard decision boundary mismatch");

        const RandomIdentity base{2026072701ULL, "stage01_foundation", "K200_S15", 2U, 17U};
        const auto first = standardGaussianFrame(base, RandomDomain::Awgn, 64U);
        const auto rerun = standardGaussianFrame(base, RandomDomain::Awgn, 64U);
        require(first == rerun, "same identity is not reproducible");

        RandomIdentity changed = base;
        ++changed.frameIndex;
        require(different(first, standardGaussianFrame(changed, RandomDomain::Awgn, 64U)),
                "frameIndex did not change AWGN");
        changed = base;
        changed.caseId = "K200_M255K207";
        require(different(first, standardGaussianFrame(changed, RandomDomain::Awgn, 64U)),
                "caseId did not change AWGN");
        changed = base;
        ++changed.ebn0Index;
        require(different(first, standardGaussianFrame(changed, RandomDomain::Awgn, 64U)),
                "ebn0Index did not change AWGN");
        changed = base;
        changed.stageId = "stage05_awgn_trial";
        require(different(first, standardGaussianFrame(changed, RandomDomain::Awgn, 64U)),
                "stageId did not change AWGN");
        require(different(first, standardGaussianFrame(base, RandomDomain::Payload, 64U)),
                "PAYLOAD and AWGN domains collided");

        const auto checkpointBefore = standardGaussianFrame(base, RandomDomain::Awgn, 64U);
        const auto checkpointAfter = standardGaussianFrame(base, RandomDomain::Awgn, 64U);
        const auto shardResult = standardGaussianFrame(base, RandomDomain::Awgn, 64U);
        require(checkpointBefore == checkpointAfter && checkpointBefore == shardResult,
                "checkpoint/resume or shard changed frame noise");
        require(payloadFrame(base, 200U) == payloadFrame(base, 200U), "payload reproducibility mismatch");

        bool rejected = false;
        try { static_cast<void>(actualRate(300U, 0U)); } catch (const std::invalid_argument&) { rejected = true; }
        require(rejected, "zero encoded length accepted");
        rejected = false;
        try {
            RandomIdentity invalid = base;
            invalid.caseId.clear();
            static_cast<void>(standardGaussianFrame(invalid, RandomDomain::Awgn, 2U));
        } catch (const std::invalid_argument&) { rejected = true; }
        require(rejected, "empty caseId accepted");
        rejected = false;
        try { static_cast<void>(bpsk(2U)); } catch (const std::invalid_argument&) { rejected = true; }
        require(rejected, "non-binary BPSK input accepted");

        std::cout << "PASS_STAGE01_FOUNDATION_UNIT\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BLOCKED_STAGE01_FOUNDATION_UNIT: " << error.what() << '\n';
        return 1;
    }
}
