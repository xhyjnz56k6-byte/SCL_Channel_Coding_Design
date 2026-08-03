#include "s5_comparison/s5.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>

namespace {

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

bool near(double a, double b, double tolerance = 1e-12) {
    return std::fabs(a - b) <= tolerance;
}

}  // namespace

int main() {
    try {
        require(s5::schemeSpecs().size() == 4, "four schemes not frozen");
        require(s5::schemeSpecs()[0].transmittedLength == 459, "R23 length mismatch");
        require(s5::schemeSpecs()[1].transmittedLength == 612, "R12 length mismatch");
        require(s5::schemeSpecs()[2].transmittedLength == 480, "N480 length mismatch");
        require(s5::schemeSpecs()[3].transmittedLength == 640, "N640 length mismatch");
        require(near(s5::sigmaSquaredFromEsN0(0.0), 0.5), "sigma formula mismatch");
        require(near(s5::burstBeta(10.0), std::sqrt(5.0)), "complex ISR beta formula mismatch");
        require(near(s5::ebN0FromEsN0(3.0, 0.5), 6.010299956639812), "Eb/N0 conversion mismatch");

        const auto noiseA = s5::complexNoise(7, 2, 1280);
        const auto noiseB = s5::complexNoise(7, 2, 1280);
        require(noiseA == noiseB && noiseA.size() == 1280, "online complex noise reproducibility mismatch");
        bool iqDifferent = false;
        for (const auto& sample : noiseA) iqDifferent = iqDifferent || sample.real() != sample.imag();
        require(iqDifferent, "I and Q must not reuse samples");

        s5::CodecContext context;
        const auto payload = s5::payloadForFrame(0);
        for (const auto& scheme : s5::schemeSpecs()) {
            const auto codeword = s5::encodeFrame(context, scheme.scheme, payload);
            require(codeword.size() == scheme.transmittedLength, "encoded length mismatch");
            const auto clean = s5::runChannel(s5::Channel::Awgn, codeword, 3.5, 0, false, false);
            for (double llr : clean.llr) require(std::fabs(llr) == 100.0, "noiseless LLR must be finite +/-100");
            const auto decoded = s5::decodeFrame(context, scheme.scheme, clean.llr);
            require(s5::bitErrors(payload, decoded.payload) == 0, "noiseless decode mismatch");

            const auto multipath = s5::runChannel(s5::Channel::Multipath, codeword, 3.5, 0, true, true);
            require(multipath.llr.size() == codeword.size(), "multipath LLR length mismatch");
            for (std::size_t i = 0; i < multipath.llr.size(); ++i) {
                require(std::isfinite(multipath.llr[i]), "multipath non-finite LLR");
                require(multipath.gain[i] > 0.0 && multipath.variance[i] > 0.0, "multipath invalid gk/vk");
            }

            const auto cfo = s5::runChannel(s5::Channel::Cfo, codeword, 3.5, 0, false, true);
            require(near(cfo.phase.front(), 0.0) && near(cfo.phase.back(), 3.14159265358979323846 / 6.0), "CFO endpoints mismatch");
            const auto doppler = s5::runChannel(s5::Channel::Doppler, codeword, 3.5, 0, false, true);
            require(doppler.phase.size() == codeword.size() && doppler.epsilon.size() == codeword.size(), "Doppler trace incomplete");
            require(doppler.epsilon.front() < 0.0 && doppler.epsilon.back() > 0.0, "Doppler frequency must cross zero");
            const auto blockage = s5::runChannel(s5::Channel::Blockage10, codeword, 3.5, 0, false, true);
            require(blockage.damageLength == static_cast<std::size_t>(std::llround(0.10 * codeword.size())), "blockage length mismatch");
            for (std::size_t i = 0; i < blockage.damageLength; ++i) require(blockage.llr[blockage.damageStart + i] == 0.0, "blocked LLR must be zero");
            const auto blockage5 = s5::runChannel(s5::Channel::Blockage5, codeword, 3.5, 0, false, true);
            require(blockage5.damageLength == static_cast<std::size_t>(std::llround(0.05 * codeword.size())), "5 percent blockage length mismatch");
            for (std::size_t i = 0; i < blockage5.damageLength; ++i) require(blockage5.llr[blockage5.damageStart + i] == 0.0, "5 percent blocked LLR must be zero");
            const auto burst = s5::runChannel(s5::Channel::Burst, codeword, 3.5, 0, false, true);
            require(burst.damageLength == static_cast<std::size_t>(std::llround(0.05 * codeword.size())), "burst length mismatch");
        }
        std::cout << "PASS_S5_UNIT\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_S5_UNIT: " << error.what() << '\n';
        return 1;
    }
}
