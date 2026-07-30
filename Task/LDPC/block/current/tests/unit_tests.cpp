#include "s4_ldpc.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>

namespace {
void check(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}
}

int main() {
    try {
        const std::vector<s4ldpc::DirectCase> first = s4ldpc::freezeS4Cases();
        const std::vector<s4ldpc::DirectCase> second = s4ldpc::freezeS4Cases();
        check(first.size() == 3, "three cases were not frozen");
        check(first[0].actualLength != first[1].actualLength, "duplicate cases");
        check(first[1].actualLength != first[2].actualLength, "duplicate cases");
        for (std::size_t index = 0; index < first.size(); ++index) {
            check(first[index].id == second[index].id, "selector is not deterministic");
            check(first[index].rankHp == first[index].parityLength, "Hp not full rank");
            const s4ldpc::DirectGraph graph = s4ldpc::buildDirectGraph(first[index]);
            const std::vector<unsigned char> payload = s4ldpc::makePayload(2026072001ULL, static_cast<int>(index), 300);
            const std::vector<unsigned char> codeword = s4ldpc::encode(graph, payload);
            check(s4ldpc::syndromeWeight(graph, codeword) == 0, "nonzero encoder syndrome");
            std::vector<double> llr(codeword.size(), 0.0);
            for (std::size_t bit = 0; bit < codeword.size(); ++bit) llr[bit] = codeword[bit] ? -20.0 : 20.0;
            const s4ldpc::DecodeResult bp = s4ldpc::decodeLayeredBp(graph, llr, 32);
            const s4ldpc::DecodeResult nms = s4ldpc::decodeLayeredNms(graph, llr, 32, 0.8);
            check(bp.numeric.nanInfCount == 0, "BP NaN/Inf");
            check(nms.numeric.nanInfCount == 0, "NMS NaN/Inf");
            check(bp.syndromePass && nms.syndromePass, "noiseless syndrome failed");
            for (int bit = 0; bit < 300; ++bit) {
                check(bp.bits[bit] == payload[bit], "BP noiseless payload mismatch");
                check(nms.bits[bit] == payload[bit], "NMS noiseless payload mismatch");
            }
        }
        std::cout << "PASS_S4_LDPC_UNIT_TESTS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_S4_LDPC_UNIT_TESTS: " << error.what() << "\n";
        return 1;
    }
}
