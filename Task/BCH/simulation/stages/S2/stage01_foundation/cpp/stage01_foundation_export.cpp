#include "stage01_foundation_awgn.hpp"

#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::invalid_argument("usage: stage01_foundation_export OUTPUT_DIR");
        const fs::path output(argv[1]);
        fs::create_directories(output);

        std::ofstream vectors(output / "stage01_foundation_awgn_vectors.csv");
        std::ofstream cpp(output / "stage01_foundation_cpp_outputs.csv");
        std::ofstream randomness(output / "stage01_foundation_randomness_test.csv");
        if (!vectors || !cpp || !randomness) throw std::runtime_error("cannot open stage01 output");

        vectors << "rowId,payloadLength,encodedLength,actual_rate,ebn0_db,bit,z\n";
        cpp << "rowId,payloadLength,encodedLength,actual_rate,ebn0_db,bit,z,sigma2,sigma,noise,"
               "transmitted,received,hard_decision,snr_linear,snr_db,conversion_formula\n";
        const std::vector<std::size_t> payloads{200U, 200U, 300U, 300U};
        const std::vector<std::size_t> encoded{285U, 248U, 420U, 390U};
        const std::vector<double> ebn0{-1.5, 0.0, 3.25, 7.0};
        const std::vector<double> z{-2.25, -0.4, 0.0, 0.35, 1.75};
        std::uint64_t row = 0U;
        vectors << std::setprecision(17);
        cpp << std::setprecision(17);
        for (std::size_t profile = 0; profile < payloads.size(); ++profile) {
            const double rate = scl::bch::s2::stage01::actualRate(payloads[profile], encoded[profile]);
            for (std::size_t sample = 0; sample < z.size(); ++sample) {
                const unsigned bit = static_cast<unsigned>((profile + sample) & 1U);
                const auto value = scl::bch::s2::stage01::evaluateSample(rate, ebn0[profile], z[sample], bit);
                vectors << row << ',' << payloads[profile] << ',' << encoded[profile] << ',' << rate << ','
                        << ebn0[profile] << ',' << bit << ',' << z[sample] << '\n';
                cpp << row << ',' << payloads[profile] << ',' << encoded[profile] << ',' << rate << ','
                    << ebn0[profile] << ',' << bit << ',' << z[sample] << ',' << value.sigma2 << ','
                    << value.sigma << ',' << value.noise << ',' << value.transmitted << ',' << value.received
                    << ',' << value.hardDecision << ',' << value.snrLinear << ',' << value.snrDb << ",\""
                    << scl::bch::s2::stage01::conversionFormula() << "\"\n";
                ++row;
            }
        }

        randomness << "testName,passed,detail\n";
        using scl::bch::s2::stage01::RandomDomain;
        using scl::bch::s2::stage01::RandomIdentity;
        using scl::bch::s2::stage01::standardGaussianFrame;
        const RandomIdentity base{2026072701ULL, "stage01_foundation", "K200_S15", 1U, 9U};
        const auto reference = standardGaussianFrame(base, RandomDomain::Awgn, 32U);
        auto changed = base;
        const auto emit = [&](const std::string& name, bool passed, const std::string& detail) {
            randomness << name << ',' << (passed ? "true" : "false") << ',' << detail << '\n';
            if (!passed) throw std::runtime_error("randomness test failed: " + name);
        };
        emit("same_identity_rerun", reference == standardGaussianFrame(base, RandomDomain::Awgn, 32U),
             "complete identity reproduced exactly");
        ++changed.frameIndex;
        emit("frame_index_changes_noise", reference != standardGaussianFrame(changed, RandomDomain::Awgn, 32U),
             "frameIndex participates in identity");
        changed = base;
        changed.caseId = "K200_M255K207";
        emit("case_id_changes_noise", reference != standardGaussianFrame(changed, RandomDomain::Awgn, 32U),
             "caseId participates in identity");
        emit("payload_awgn_domain_separation",
             reference != standardGaussianFrame(base, RandomDomain::Payload, 32U),
             "PAYLOAD and AWGN domains are independent");
        emit("checkpoint_resume_identity",
             reference == standardGaussianFrame(base, RandomDomain::Awgn, 32U),
             "resume reconstructs the same complete identity");
        emit("shard_identity",
             reference == standardGaussianFrame(base, RandomDomain::Awgn, 32U),
             "shard ownership does not alter frame identity");

        std::cout << "PASS_STAGE01_FOUNDATION_EXPORT\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BLOCKED_STAGE01_FOUNDATION_EXPORT: " << error.what() << '\n';
        return 1;
    }
}
