#include "common/awgn_channel.hpp"
#include "common/demodulation.hpp"
#include "common/modulation.hpp"

#include <cmath>
#include <functional>
#include <stdexcept>
#include <string>

namespace {
void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void requireNear(double actual, double expected, double tolerance, const std::string& message) {
    if (std::fabs(actual - expected) > tolerance) {
        throw std::runtime_error(message);
    }
}

void requireThrows(const std::string& name, const std::function<void()>& fn) {
    try {
        fn();
    } catch (const std::exception&) {
        return;
    }
    throw std::runtime_error(name + " did not fail");
}
}

int main() {
    require(scl::common::bpskSymbol(0U) == 1.0, "BPSK bit 0 mismatch");
    require(scl::common::bpskSymbol(1U) == -1.0, "BPSK bit 1 mismatch");
    requireThrows("bad bit", [] { (void)scl::common::bpskSymbol(2U); });

    scl::common::CodeLengths r200;
    r200.payloadLength = 200;
    r200.codecInputLength = 200;
    r200.encodedLength = 248;
    r200.transmittedLength = 248;
    scl::common::CodeLengths r300;
    r300.payloadLength = 300;
    r300.codecInputLength = 300;
    r300.encodedLength = 390;
    r300.transmittedLength = 390;
    requireNear(scl::common::computeCodeRate(r200), 200.0 / 248.0, 1e-15, "R=200/248 mismatch");
    requireNear(scl::common::computeCodeRate(r300), 300.0 / 390.0, 1e-15, "R=300/390 mismatch");
    const double sigma = scl::common::computeAwgnSigma(r200, 2.0);
    const auto received = scl::common::applyAwgn({1.0, -1.0}, {0.5, -0.5}, sigma);
    requireNear(received[0], 1.0 + 0.5 * sigma, 1e-15, "AWGN sample 0 mismatch");
    requireNear(received[1], -1.0 - 0.5 * sigma, 1e-15, "AWGN sample 1 mismatch");
    require(scl::common::hardDecisionBit(0.0) == 0U, "hard decision at zero mismatch");
    require(scl::common::hardDecisionBit(-0.1) == 1U, "hard decision negative mismatch");
    require(scl::common::llrSignDecisionBit(scl::common::llrValue(0.25, sigma)) == 0U, "LLR positive decision mismatch");
    requireThrows("noise length mismatch", [&] { (void)scl::common::applyAwgn({1.0}, {1.0, 2.0}, sigma); });
    requireThrows("bad sigma", [] { (void)scl::common::computeLlr({1.0}, 0.0); });
    return 0;
}
