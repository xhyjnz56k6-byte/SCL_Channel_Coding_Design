#include "s4_ldpc.hpp"
#include "nr_tables.hpp"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <limits>
#include <random>
#include <stdexcept>

namespace s4ldpc {
namespace {

// Stage23g does not impose a low LLR/message saturation threshold.  Keep only
// an overflow guard so that subtracting an old layered message remains exact
// over the practical operating range.
constexpr double kLlrClip = 1.0e6;
constexpr double kMessageClip = 1.0e6;
constexpr double kAtanhEps = 1e-16;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

std::uint64_t mix(std::uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30U)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27U)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31U);
}

int parity64(std::uint64_t x) {
    x ^= x >> 32U;
    x ^= x >> 16U;
    x ^= x >> 8U;
    x ^= x >> 4U;
    return static_cast<int>((0x6996U >> (x & 15U)) & 1U);
}

int dotBits(const std::vector<std::uint64_t>& a, const std::vector<std::uint64_t>& b) {
    int value = 0;
    for (std::size_t index = 0; index < a.size(); ++index) value ^= parity64(a[index] & b[index]);
    return value;
}

int setIndexForZc(int zc) {
    for (int row = 0; row < 8; ++row) {
        for (int column = 0; column < 8; ++column) {
            if (liftSizeTable[row][column] == zc) return row;
        }
    }
    return -1;
}

std::vector<Edge> expandEdges(const DirectCase& config) {
    std::vector<Edge> result;
    for (int index = 0; index < 197; ++index) {
        const int baseRow = shiftTableBgn_2[index][0];
        const int baseColumn = shiftTableBgn_2[index][1];
        if (baseRow >= config.mb || baseColumn >= config.nb) continue;
        const int shift = shiftTableBgn_2[index][config.setIndex + 2] % config.zc;
        for (int z = 0; z < config.zc; ++z) {
            Edge edge;
            edge.row = baseRow * config.zc + z;
            edge.col = baseColumn * config.zc + ((z + shift) % config.zc);
            result.push_back(edge);
        }
    }
    std::sort(result.begin(), result.end(), [](const Edge& left, const Edge& right) {
        if (left.row != right.row) return left.row < right.row;
        return left.col < right.col;
    });
    return result;
}

int gf2Rank(int rows, int columns, const std::vector<Edge>& edges, int columnStart) {
    const int words = (columns + 63) / 64;
    std::vector<std::vector<std::uint64_t> > matrix(
        rows, std::vector<std::uint64_t>(static_cast<std::size_t>(words), 0));
    for (const Edge& edge : edges) {
        const int column = edge.col - columnStart;
        if (column >= 0 && column < columns) {
            matrix[edge.row][column / 64] ^= (1ULL << (column % 64));
        }
    }
    int rank = 0;
    for (int column = 0; column < columns && rank < rows; ++column) {
        int pivot = -1;
        for (int row = rank; row < rows; ++row) {
            if ((matrix[row][column / 64] >> (column % 64)) & 1ULL) {
                pivot = row;
                break;
            }
        }
        if (pivot < 0) continue;
        std::swap(matrix[rank], matrix[pivot]);
        for (int row = rank + 1; row < rows; ++row) {
            if ((matrix[row][column / 64] >> (column % 64)) & 1ULL) {
                for (int word = 0; word < words; ++word) matrix[row][word] ^= matrix[rank][word];
            }
        }
        ++rank;
    }
    return rank;
}

double clipped(double value, double limit, std::uint64_t& counter) {
    if (value > limit) {
        ++counter;
        return limit;
    }
    if (value < -limit) {
        ++counter;
        return -limit;
    }
    return value;
}

void hardDecision(const std::vector<double>& posterior, std::vector<unsigned char>& bits) {
    for (std::size_t index = 0; index < posterior.size(); ++index) {
        bits[index] = posterior[index] < 0.0 ? 1U : 0U;
    }
}

int payloadErrors(const std::vector<unsigned char>* referencePayload,
                  const std::vector<unsigned char>& bits) {
    if (referencePayload == nullptr) return -1;
    int errors = 0;
    for (std::size_t index = 0; index < referencePayload->size(); ++index) {
        errors += (*referencePayload)[index] != bits[index];
    }
    return errors;
}

void captureIteration(DecodeResult& result,
                      const std::vector<double>& posterior,
                      const std::vector<double>& messages,
                      const std::vector<unsigned char>* referencePayload) {
    IterationTrace point;
    point.iteration = result.usedIterations;
    point.syndromeWeight = result.finalSyndromeWeight;
    point.payloadErrorCount = payloadErrors(referencePayload, result.bits);
    point.hardDecisionHash = hashBytes(result.bits);
    point.posteriorLlrHash = hashDoubles(posterior);
    point.checkMessageHash = hashDoubles(messages);
    result.trace.push_back(point);
}

DirectCase evaluateCase(int payloadLength, int zc, int nb) {
    DirectCase config;
    config.payloadLength = payloadLength;
    config.zc = zc;
    config.setIndex = setIndexForZc(zc);
    config.nb = nb;
    config.mb = nb - config.kb;
    config.informationCapacity = config.kb * zc;
    config.fillerLength = config.informationCapacity - payloadLength;
    config.parityLength = config.mb * zc;
    config.actualLength = nb * zc;
    config.actualRate = static_cast<double>(payloadLength) / config.actualLength;
    const std::vector<Edge> edges = expandEdges(config);
    config.rankH = gf2Rank(config.parityLength, config.actualLength, edges, 0);
    config.rankHp = gf2Rank(config.parityLength, config.parityLength, edges, config.informationCapacity);
    config.encodable = config.fillerLength >= 0
        && config.parityLength > 0
        && config.rankHp == config.parityLength;
    if (!config.encodable) {
        if (config.fillerLength < 0) config.rejectionReason = "INFORMATION_CAPACITY_LT_PAYLOAD";
        else if (config.parityLength <= 0) config.rejectionReason = "NO_PARITY";
        else config.rejectionReason = "HP_NOT_FULL_RANK";
    }
    config.id = "LDPC_BG2_K" + std::to_string(payloadLength) + "_N" + std::to_string(config.actualLength);
    return config;
}

} // namespace

std::vector<DirectCase> enumerateDirectCases(int payloadLength, int maxLength) {
    std::vector<int> zcValues;
    for (int row = 0; row < 8; ++row) {
        for (int column = 0; column < 8; ++column) {
            const int zc = liftSizeTable[row][column];
            if (zc > 0 && std::find(zcValues.begin(), zcValues.end(), zc) == zcValues.end()) zcValues.push_back(zc);
        }
    }
    std::sort(zcValues.begin(), zcValues.end());
    std::vector<DirectCase> result;
    for (int zc : zcValues) {
        if (8 * zc < payloadLength) continue;
        const int maximumNb = std::min(52, maxLength / zc);
        for (int nb = 9; nb <= maximumNb; ++nb) result.push_back(evaluateCase(payloadLength, zc, nb));
    }
    std::sort(result.begin(), result.end(), [](const DirectCase& left, const DirectCase& right) {
        if (left.actualLength != right.actualLength) return left.actualLength < right.actualLength;
        if (left.zc != right.zc) return left.zc < right.zc;
        return left.nb < right.nb;
    });
    return result;
}

DirectCase selectDirectCase(int payloadLength, int targetLength, double targetRate, int baseGraph, int maxLength) {
    require(baseGraph == 2, "S4 supports BG2 only");
    const std::vector<DirectCase> candidates = enumerateDirectCases(payloadLength, maxLength);
    std::vector<DirectCase> feasible;
    for (const DirectCase& candidate : candidates) if (candidate.encodable) feasible.push_back(candidate);
    require(!feasible.empty(), "no encodable Direct BG2 candidate");
    std::sort(feasible.begin(), feasible.end(), [targetLength, targetRate](const DirectCase& left, const DirectCase& right) {
        const int leftLength = std::abs(left.actualLength - targetLength);
        const int rightLength = std::abs(right.actualLength - targetLength);
        if (leftLength != rightLength) return leftLength < rightLength;
        const double leftRate = std::fabs(left.actualRate - targetRate);
        const double rightRate = std::fabs(right.actualRate - targetRate);
        if (leftRate != rightRate) return leftRate < rightRate;
        if (left.zc != right.zc) return left.zc < right.zc;
        return left.nb < right.nb;
    });
    DirectCase selected = feasible.front();
    selected.targetLength = targetLength;
    return selected;
}

std::vector<DirectCase> freezeS4Cases() {
    std::vector<DirectCase> result;
    result.push_back(selectDirectCase(300, 480, 300.0 / 480.0, 2, 640));
    result.push_back(selectDirectCase(300, 576, 300.0 / 576.0, 2, 640));
    std::vector<DirectCase> candidates = enumerateDirectCases(300, 640);
    std::sort(candidates.begin(), candidates.end(), [](const DirectCase& left, const DirectCase& right) {
        if (left.actualLength != right.actualLength) return left.actualLength > right.actualLength;
        return left.zc < right.zc;
    });
    for (const DirectCase& candidate : candidates) {
        if (!candidate.encodable) continue;
        if (candidate.actualLength == result[0].actualLength || candidate.actualLength == result[1].actualLength) continue;
        DirectCase selected = candidate;
        selected.targetLength = 640;
        result.push_back(selected);
        break;
    }
    require(result.size() == 3, "failed to freeze three distinct cases");
    return result;
}

DirectGraph buildDirectGraph(const DirectCase& config) {
    require(config.encodable, "cannot build non-encodable graph");
    DirectGraph graph;
    graph.config = config;
    graph.edges = expandEdges(config);
    graph.rowEdges.assign(config.parityLength, std::vector<int>());
    graph.edgeColumns.resize(graph.edges.size());
    for (std::size_t index = 0; index < graph.edges.size(); ++index) {
        graph.rowEdges[graph.edges[index].row].push_back(static_cast<int>(index));
        graph.edgeColumns[index] = graph.edges[index].col;
    }
    const int size = config.parityLength;
    const int words = (size + 63) / 64;
    std::vector<std::vector<std::uint64_t> > hp(
        size, std::vector<std::uint64_t>(static_cast<std::size_t>(words), 0));
    graph.encoderTransform.assign(size, std::vector<std::uint64_t>(static_cast<std::size_t>(words), 0));
    for (int row = 0; row < size; ++row) graph.encoderTransform[row][row / 64] |= 1ULL << (row % 64);
    for (const Edge& edge : graph.edges) {
        if (edge.col >= config.informationCapacity) {
            const int parityColumn = edge.col - config.informationCapacity;
            hp[edge.row][parityColumn / 64] ^= 1ULL << (parityColumn % 64);
        }
    }
    for (int column = 0, rank = 0; column < size && rank < size; ++column) {
        int pivot = -1;
        for (int row = rank; row < size; ++row) {
            if ((hp[row][column / 64] >> (column % 64)) & 1ULL) {
                pivot = row;
                break;
            }
        }
        if (pivot < 0) continue;
        std::swap(hp[rank], hp[pivot]);
        std::swap(graph.encoderTransform[rank], graph.encoderTransform[pivot]);
        for (int row = 0; row < size; ++row) {
            if (row != rank && ((hp[row][column / 64] >> (column % 64)) & 1ULL)) {
                for (int word = 0; word < words; ++word) {
                    hp[row][word] ^= hp[rank][word];
                    graph.encoderTransform[row][word] ^= graph.encoderTransform[rank][word];
                }
            }
        }
        graph.pivotColumns.push_back(column);
        ++rank;
    }
    require(static_cast<int>(graph.pivotColumns.size()) == size, "Hp rank changed during graph build");
    return graph;
}

std::vector<unsigned char> encode(const DirectGraph& graph, const std::vector<unsigned char>& payload) {
    const DirectCase& config = graph.config;
    require(static_cast<int>(payload.size()) == config.payloadLength, "payload length mismatch");
    std::vector<unsigned char> codeword(config.actualLength, 0);
    std::copy(payload.begin(), payload.end(), codeword.begin());
    const int words = (config.parityLength + 63) / 64;
    std::vector<std::uint64_t> rhs(static_cast<std::size_t>(words), 0);
    for (const Edge& edge : graph.edges) {
        if (edge.col < config.informationCapacity && codeword[edge.col]) {
            rhs[edge.row / 64] ^= 1ULL << (edge.row % 64);
        }
    }
    for (int row = 0; row < config.parityLength; ++row) {
        if (dotBits(graph.encoderTransform[row], rhs)) {
            codeword[config.informationCapacity + graph.pivotColumns[row]] = 1U;
        }
    }
    require(syndromeWeight(graph, codeword) == 0, "encoder produced nonzero syndrome");
    return codeword;
}

int syndromeWeight(const DirectGraph& graph, const std::vector<unsigned char>& bits) {
    require(static_cast<int>(bits.size()) == graph.config.actualLength, "syndrome length mismatch");
    std::vector<unsigned char> syndrome(graph.config.parityLength, 0);
    for (const Edge& edge : graph.edges) syndrome[edge.row] ^= bits[edge.col] & 1U;
    int weight = 0;
    for (unsigned char value : syndrome) weight += value != 0;
    return weight;
}

DecodeResult decodeLayeredBp(const DirectGraph& graph,
                             const std::vector<double>& llr,
                             int maxIterations,
                             EarlyStopPolicy policy,
                             const std::vector<unsigned char>* referencePayload,
                             bool captureTrace) {
    require(static_cast<int>(llr.size()) == graph.config.actualLength, "BP LLR length mismatch");
    std::vector<double> posterior = llr;
    std::vector<double> messages(graph.edges.size(), 0.0);
    DecodeResult result;
    result.bits.assign(llr.size(), 0);
    for (double& value : posterior) value = clipped(value, kLlrClip, result.numeric.llrClampCount);
    for (int iteration = 0; iteration < maxIterations; ++iteration) {
        for (const std::vector<int>& ids : graph.rowEdges) {
            if (ids.empty()) continue;
            ++result.complexity.checkNodeUpdates;
            const int degree = static_cast<int>(ids.size());
            std::vector<double> extrinsic(degree, 0.0);
            std::vector<double> prefix(degree + 1, 1.0);
            std::vector<double> suffix(degree + 1, 1.0);
            for (int index = 0; index < degree; ++index) {
                const int edge = ids[index];
                extrinsic[index] = posterior[graph.edgeColumns[edge]] - messages[edge];
                prefix[index + 1] = prefix[index] * std::tanh(0.5 * extrinsic[index]);
                ++result.complexity.tanhOperations;
            }
            for (int index = degree - 1; index >= 0; --index) {
                suffix[index] = suffix[index + 1] * std::tanh(0.5 * extrinsic[index]);
                ++result.complexity.tanhOperations;
            }
            for (int index = 0; index < degree; ++index) {
                const int edge = ids[index];
                const int column = graph.edgeColumns[edge];
                double product = prefix[index] * suffix[index + 1];
                if (product > 1.0 - kAtanhEps) {
                    product = 1.0 - kAtanhEps;
                    ++result.numeric.atanhClampCount;
                } else if (product < -1.0 + kAtanhEps) {
                    product = -1.0 + kAtanhEps;
                    ++result.numeric.atanhClampCount;
                }
                double message = 2.0 * std::atanh(product);
                ++result.complexity.atanhOperations;
                if (!std::isfinite(message) || !std::isfinite(extrinsic[index])) {
                    ++result.numeric.nanInfCount;
                    message = 0.0;
                }
                message = clipped(message, kMessageClip, result.numeric.messageClampCount);
                messages[edge] = message;
                posterior[column] = clipped(extrinsic[index] + message, kLlrClip, result.numeric.llrClampCount);
                ++result.complexity.messageUpdates;
                ++result.complexity.variableNodeUpdates;
            }
        }
        hardDecision(posterior, result.bits);
        result.usedIterations = iteration + 1;
        result.finalSyndromeWeight = syndromeWeight(graph, result.bits);
        if (captureTrace) captureIteration(result, posterior, messages, referencePayload);
        if (policy == EarlyStopPolicy::SyndromeAfterFullIteration
            && result.finalSyndromeWeight == 0) break;
    }
    result.syndromePass = result.finalSyndromeWeight == 0;
    return result;
}

DecodeResult decodeLayeredNms(const DirectGraph& graph,
                              const std::vector<double>& llr,
                              int maxIterations,
                              double alpha,
                              EarlyStopPolicy policy,
                              const std::vector<unsigned char>* referencePayload,
                              bool captureTrace) {
    require(alpha > 0.0 && alpha <= 1.0, "NMS alpha outside (0,1]");
    require(static_cast<int>(llr.size()) == graph.config.actualLength, "NMS LLR length mismatch");
    std::vector<double> posterior = llr;
    std::vector<double> messages(graph.edges.size(), 0.0);
    DecodeResult result;
    result.bits.assign(llr.size(), 0);
    for (double& value : posterior) value = clipped(value, kLlrClip, result.numeric.llrClampCount);
    for (int iteration = 0; iteration < maxIterations; ++iteration) {
        for (const std::vector<int>& ids : graph.rowEdges) {
            if (ids.empty()) continue;
            ++result.complexity.checkNodeUpdates;
            const int degree = static_cast<int>(ids.size());
            std::vector<double> extrinsic(degree, 0.0);
            double min1 = std::numeric_limits<double>::infinity();
            double min2 = std::numeric_limits<double>::infinity();
            int minIndex = -1;
            int signProduct = 1;
            for (int index = 0; index < degree; ++index) {
                const int edge = ids[index];
                extrinsic[index] = posterior[graph.edgeColumns[edge]] - messages[edge];
                const double magnitude = std::fabs(extrinsic[index]);
                ++result.complexity.absOperations;
                result.complexity.comparisonOperations += 2;
                if (magnitude < min1) {
                    min2 = min1;
                    min1 = magnitude;
                    minIndex = index;
                    ++result.complexity.min1Min2Updates;
                } else if (magnitude < min2) {
                    min2 = magnitude;
                    ++result.complexity.min1Min2Updates;
                }
                const int sign = extrinsic[index] < 0.0 ? -1 : 1;
                signProduct *= sign;
                ++result.complexity.signOperations;
            }
            if (degree == 1) {
                min1 = 0.0;
                min2 = 0.0;
            }
            for (int index = 0; index < degree; ++index) {
                const int edge = ids[index];
                const int column = graph.edgeColumns[edge];
                const int ownSign = extrinsic[index] < 0.0 ? -1 : 1;
                const double selected = index == minIndex ? min2 : min1;
                double message = alpha * selected * signProduct * ownSign;
                ++result.complexity.alphaMultiplications;
                if (!std::isfinite(message) || !std::isfinite(extrinsic[index])) {
                    ++result.numeric.nanInfCount;
                    message = 0.0;
                }
                message = clipped(message, kMessageClip, result.numeric.messageClampCount);
                messages[edge] = message;
                posterior[column] = clipped(extrinsic[index] + message, kLlrClip, result.numeric.llrClampCount);
                ++result.complexity.messageUpdates;
                ++result.complexity.variableNodeUpdates;
            }
        }
        hardDecision(posterior, result.bits);
        result.usedIterations = iteration + 1;
        result.finalSyndromeWeight = syndromeWeight(graph, result.bits);
        if (captureTrace) captureIteration(result, posterior, messages, referencePayload);
        if (policy == EarlyStopPolicy::SyndromeAfterFullIteration
            && result.finalSyndromeWeight == 0) break;
    }
    result.syndromePass = result.finalSyndromeWeight == 0;
    return result;
}

std::vector<unsigned char> makePayload(std::uint64_t payloadSeed, int frameIndex, int payloadLength) {
    std::mt19937_64 random(mix(payloadSeed ^ static_cast<std::uint64_t>(frameIndex) * 0x100000001b3ULL));
    std::vector<unsigned char> payload(payloadLength, 0);
    for (unsigned char& bit : payload) bit = static_cast<unsigned char>(random() & 1ULL);
    return payload;
}

std::vector<double> makeChannelLlr(const DirectCase& config,
                                   const std::vector<unsigned char>& codeword,
                                   std::uint64_t noiseSeed,
                                   std::uint64_t noiseGroup,
                                   int frameIndex,
                                   double esN0Db) {
    require(static_cast<int>(codeword.size()) == config.actualLength, "channel codeword length mismatch");
    std::mt19937_64 random(mix(noiseSeed ^ noiseGroup * 0xd1342543de82ef95ULL
                              ^ static_cast<std::uint64_t>(frameIndex) * 0x9e3779b97f4a7c15ULL));
    std::normal_distribution<double> normal(0.0, 1.0);
    const double sigmaSquared = 1.0 / (2.0 * std::pow(10.0, esN0Db / 10.0));
    const double sigma = std::sqrt(sigmaSquared);
    std::vector<double> llr(codeword.size(), 0.0);
    for (std::size_t index = 0; index < codeword.size(); ++index) {
        const double symbol = codeword[index] ? -1.0 : 1.0;
        const double received = symbol + sigma * normal(random);
        llr[index] = 2.0 * received / sigmaSquared;
    }
    return llr;
}

std::uint64_t hashBytes(const std::vector<unsigned char>& values) {
    std::uint64_t hash = 1469598103934665603ULL;
    for (unsigned char value : values) {
        hash ^= value;
        hash *= 1099511628211ULL;
    }
    return hash;
}

std::uint64_t hashDoubles(const std::vector<double>& values) {
    std::uint64_t hash = 1469598103934665603ULL;
    for (double value : values) {
        std::uint64_t bits = 0;
        std::memcpy(&bits, &value, sizeof(bits));
        for (int byte = 0; byte < 8; ++byte) {
            hash ^= static_cast<unsigned char>((bits >> (8 * byte)) & 0xffU);
            hash *= 1099511628211ULL;
        }
    }
    return hash;
}

} // namespace s4ldpc
