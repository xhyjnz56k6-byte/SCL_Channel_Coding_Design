#ifndef SCL_BCH_S2_STAGE01_FOUNDATION_AWGN_HPP
#define SCL_BCH_S2_STAGE01_FOUNDATION_AWGN_HPP

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace scl::bch::s2::stage01 {

enum class RandomDomain : std::uint64_t {
    Payload = 0x5041594c4f414431ULL,
    Awgn = 0x4157474e5f303031ULL
};

struct RandomIdentity {
    std::uint64_t masterSeed = 0U;
    std::string stageId;
    std::string caseId;
    std::uint64_t ebn0Index = 0U;
    std::uint64_t frameIndex = 0U;
};

struct AwgnSample {
    double actualRate = 0.0;
    double ebn0Db = 0.0;
    double sigma2 = 0.0;
    double sigma = 0.0;
    double standardGaussian = 0.0;
    double noise = 0.0;
    double transmitted = 0.0;
    double received = 0.0;
    unsigned hardDecision = 0U;
    double snrLinear = 0.0;
    double snrDb = 0.0;
};

std::uint64_t stableTextId(const std::string& text);
std::uint64_t randomWord(const RandomIdentity& identity,
                         RandomDomain domain,
                         std::uint64_t symbolIndex,
                         std::uint64_t lane);
double standardGaussian(const RandomIdentity& identity,
                        RandomDomain domain,
                        std::uint64_t symbolIndex);
std::vector<double> standardGaussianFrame(const RandomIdentity& identity,
                                          RandomDomain domain,
                                          std::size_t symbolCount);
std::vector<unsigned> payloadFrame(const RandomIdentity& identity,
                                   std::size_t payloadLength);
double actualRate(std::size_t payloadLength, std::size_t encodedLength);
double awgnSigma2(double rate, double ebn0Db);
double snrLinear(double rate, double ebn0Db);
double snrDb(double rate, double ebn0Db);
double bpsk(unsigned bit);
unsigned hardDecision(double received);
AwgnSample evaluateSample(double rate, double ebn0Db, double z, unsigned bit);
const char* conversionFormula();

}  // namespace scl::bch::s2::stage01

#endif
