#include "common/awgn_channel.hpp"
#include "common/demodulation.hpp"
#include "common/gaussian_noise.hpp"
#include "common/modulation.hpp"
#include "common/random_policy.hpp"

#include <fstream>
#include <iomanip>
#include <stdexcept>
#include <string>

int main(int argc, char** argv) {
    if (argc != 2) {
        return 1;
    }
    try {
        std::ofstream output(argv[1]);
        if (!output) throw std::runtime_error("failed to open reference output");
        scl::common::CodeLengths lengths{200U, 200U, 248U, 248U};
        const double sigma = scl::common::computeAwgnSigma(lengths, 2.0);
        const double received = scl::common::applyAwgn({1.0}, {0.5}, sigma).front();
        const double llr = scl::common::llrValue(received, sigma);
        output << std::setprecision(17);
        output << "field,value\n";
        output << "noiseWord0," << scl::common::noiseUniformWord({2026072101ULL, 0ULL, 0ULL, 0ULL, 1ULL}) << '\n';
        output << "noiseWord1," << scl::common::noiseUniformWord({2026072101ULL, 0ULL, 0ULL, 1ULL, 1ULL}) << '\n';
        output << "gaussian0," << scl::common::standardGaussianSample({2026072101ULL, 0ULL, 0ULL, 0ULL, 1ULL}) << '\n';
        output << "bpsk0," << scl::common::bpskSymbol(0U) << '\n';
        output << "bpsk1," << scl::common::bpskSymbol(1U) << '\n';
        output << "codeRate," << scl::common::computeCodeRate(lengths) << '\n';
        output << "sigma," << sigma << '\n';
        output << "received," << received << '\n';
        output << "llr," << llr << '\n';
        output << "hardDecision," << static_cast<unsigned>(scl::common::hardDecisionBit(received)) << '\n';
        output << "llrSignDecision," << static_cast<unsigned>(scl::common::llrSignDecisionBit(llr)) << '\n';
    } catch (...) {
        return 1;
    }
    return 0;
}
