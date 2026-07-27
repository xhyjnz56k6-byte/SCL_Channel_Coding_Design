#include "stage02_case_contract.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <set>
#include <stdexcept>
#include <string>

namespace {

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

scl::common::BitVector pattern(std::size_t length, unsigned mode) {
    scl::common::BitVector bits(length, 0U);
    for (std::size_t i = 0; i < length; ++i) {
        if (mode == 1U) bits[i] = 1U;
        else if (mode == 2U) bits[i] = static_cast<scl::common::Bit>(i & 1U);
        else if (mode == 3U) bits[i] = static_cast<scl::common::Bit>((i * 17U + 5U) & 1U);
    }
    return bits;
}

}  // namespace

int main() {
    try {
        using namespace scl::bch::s2::stage02;
        const auto& contracts = allCaseContracts();
        require(contracts.size() == 8U, "contract count is not 8");
        std::set<std::string> ids;
        std::set<std::string> names;
        std::set<std::string> payloadStylePairs;
        for (const auto& contract : contracts) {
            validateCaseContract(contract);
            require(ids.insert(contract.caseId).second, "duplicate caseId");
            require(names.insert(contract.displayName).second, "duplicate displayName");
            require(payloadStylePairs.insert(std::to_string(contract.payloadLength) + ":" +
                                             contract.plotStyle.id).second,
                    "duplicate style within payload group");
            require(std::abs(contract.actualRate -
                    static_cast<double>(contract.payloadLength) / contract.totalEncodedLength) < 1e-15,
                    "actualRate mismatch");
            for (unsigned mode = 0U; mode < 4U; ++mode) {
                const auto payload = pattern(contract.payloadLength, mode);
                const auto encoded = encodeFrame(contract.id, payload);
                const auto decoded = decodeFrame(contract.id, encoded.encodedBits);
                require(encoded.encodedBits.size() == contract.totalEncodedLength, "encoded length mismatch");
                require(decoded.payload == payload, "contract encode/decode recovery mismatch");
                require(decoded.reportedSuccess && decoded.failedBlocks == 0U, "noiseless status mismatch");
            }
        }
        const auto& multi = caseContract(CaseId::K300_M255K207);
        require(multi.blockCount == 2U && multi.payloadPerBlock == std::vector<std::size_t>({150U, 150U}),
                "K300 M255 framing is not frozen 150+150");
        require(multi.totalEncodedLength == 396U && multi.actualRate == 300.0 / 396.0,
                "K300 M255 aggregate length/rate mismatch");

        bool rejected = false;
        try { static_cast<void>(caseContract(static_cast<CaseId>(99))); }
        catch (const std::invalid_argument&) { rejected = true; }
        require(rejected, "invalid CaseId accepted");
        rejected = false;
        try { static_cast<void>(encodeFrame(CaseId::K200_S15, scl::common::BitVector(199U, 0U))); }
        catch (const std::invalid_argument&) { rejected = true; }
        require(rejected, "invalid payload length accepted");
        rejected = false;
        try { static_cast<void>(decodeFrame(CaseId::K300_M255K207, scl::common::BitVector(395U, 0U))); }
        catch (const std::invalid_argument&) { rejected = true; }
        require(rejected, "invalid received length accepted");

        std::cout << "PASS_STAGE02_CASE_CONTRACT_UNIT\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BLOCKED_STAGE02_CASE_CONTRACT_UNIT: " << error.what() << '\n';
        return 1;
    }
}
