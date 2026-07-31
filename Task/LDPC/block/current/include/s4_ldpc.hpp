#ifndef S4_LDPC_HPP
#define S4_LDPC_HPP

#include <cstdint>
#include <string>
#include <vector>

namespace s4ldpc {

struct DirectCase {
    std::string id;
    int targetLength = 0;
    int payloadLength = 300;
    int bg = 2;
    int zc = 0;
    int setIndex = 0;
    int kb = 8;
    int nb = 0;
    int mb = 0;
    int informationCapacity = 0;
    int fillerLength = 0;
    int parityLength = 0;
    int actualLength = 0;
    double actualRate = 0.0;
    int rankH = 0;
    int rankHp = 0;
    bool encodable = false;
    std::string rejectionReason;
};

struct Edge {
    int row = 0;
    int col = 0;
};

struct DirectGraph {
    DirectCase config;
    std::vector<Edge> edges;
    std::vector<std::vector<int> > rowEdges;
    std::vector<int> edgeColumns;
    std::vector<int> pivotColumns;
    std::vector<std::vector<std::uint64_t> > encoderTransform;
};

struct NumericStats {
    std::uint64_t atanhClampCount = 0;
    std::uint64_t nanInfCount = 0;
    std::uint64_t llrClampCount = 0;
    std::uint64_t messageClampCount = 0;
};

struct ComplexityStats {
    std::uint64_t checkNodeUpdates = 0;
    std::uint64_t variableNodeUpdates = 0;
    std::uint64_t messageUpdates = 0;
    std::uint64_t tanhOperations = 0;
    std::uint64_t atanhOperations = 0;
    std::uint64_t absOperations = 0;
    std::uint64_t comparisonOperations = 0;
    std::uint64_t min1Min2Updates = 0;
    std::uint64_t signOperations = 0;
    std::uint64_t alphaMultiplications = 0;
};

enum class EarlyStopPolicy {
    SyndromeAfterFullIteration,
    IterationLimitOnly
};

struct IterationTrace {
    int iteration = 0;
    int syndromeWeight = 0;
    int payloadErrorCount = -1;
    std::uint64_t hardDecisionHash = 0;
    std::uint64_t posteriorLlrHash = 0;
    std::uint64_t checkMessageHash = 0;
};

struct DecodeResult {
    std::vector<unsigned char> bits;
    int usedIterations = 0;
    int finalSyndromeWeight = 0;
    bool syndromePass = false;
    NumericStats numeric;
    ComplexityStats complexity;
    std::vector<IterationTrace> trace;
};

std::vector<DirectCase> enumerateDirectCases(int payloadLength, int maxLength);
DirectCase selectDirectCase(int payloadLength, int targetLength, double targetRate, int baseGraph, int maxLength);
std::vector<DirectCase> freezeS4Cases();
DirectGraph buildDirectGraph(const DirectCase& config);
std::vector<unsigned char> encode(const DirectGraph& graph, const std::vector<unsigned char>& payload);
int syndromeWeight(const DirectGraph& graph, const std::vector<unsigned char>& bits);
DecodeResult decodeLayeredBp(
    const DirectGraph& graph,
    const std::vector<double>& llr,
    int maxIterations,
    EarlyStopPolicy policy = EarlyStopPolicy::SyndromeAfterFullIteration,
    const std::vector<unsigned char>* referencePayload = nullptr,
    bool captureTrace = false);
DecodeResult decodeLayeredNms(
    const DirectGraph& graph,
    const std::vector<double>& llr,
    int maxIterations,
    double alpha,
    EarlyStopPolicy policy = EarlyStopPolicy::SyndromeAfterFullIteration,
    const std::vector<unsigned char>* referencePayload = nullptr,
    bool captureTrace = false);
std::vector<double> makeChannelLlr(const DirectCase& config,
                                   const std::vector<unsigned char>& codeword,
                                   std::uint64_t noiseSeed,
                                   std::uint64_t noiseGroup,
                                   int frameIndex,
                                   double esN0Db);
std::vector<unsigned char> makePayload(std::uint64_t payloadSeed, int frameIndex, int payloadLength);
std::uint64_t hashBytes(const std::vector<unsigned char>& values);
std::uint64_t hashDoubles(const std::vector<double>& values);

} // namespace s4ldpc

#endif
