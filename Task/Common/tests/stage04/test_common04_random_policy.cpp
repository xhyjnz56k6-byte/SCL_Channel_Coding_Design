#include "common/random_policy.hpp"

#include <functional>
#include <stdexcept>
#include <string>

namespace {
void require(bool condition, const std::string& message) {
    if (!condition) {
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
    const scl::common::NoiseKey key{2026072101ULL, 0ULL, 12ULL, 34ULL, scl::common::kNoisePolicyVersion};
    require(scl::common::noiseUniformWord(key) == scl::common::noiseUniformWord(key), "same key mismatch");
    require(scl::common::noiseUniformWord(key) != scl::common::noiseUniformWord({2026072102ULL, 0ULL, 12ULL, 34ULL, 1ULL}), "seed sample collision");
    require(scl::common::noiseUniformWord(key) != scl::common::noiseUniformWord({2026072101ULL, 1ULL, 12ULL, 34ULL, 1ULL}), "group sample collision");
    require(scl::common::noiseUniformWord(key) != scl::common::noiseUniformWord({2026072101ULL, 0ULL, 13ULL, 34ULL, 1ULL}), "frame sample collision");
    require(scl::common::noiseUniformWord(key) != scl::common::noiseUniformWord({2026072101ULL, 0ULL, 12ULL, 35ULL, 1ULL}), "symbol sample collision");
    requireThrows("bad policy", [] { (void)scl::common::noiseUniformWord({1ULL, 0ULL, 0ULL, 0ULL, 999ULL}); });

    const auto continuous = scl::common::generateNoiseWords(7ULL, 0ULL, 0ULL, 4ULL, 5ULL);
    const auto first = scl::common::generateNoiseWords(7ULL, 0ULL, 0ULL, 2ULL, 5ULL);
    const auto second = scl::common::generateNoiseWords(7ULL, 0ULL, 2ULL, 2ULL, 5ULL);
    require(continuous.size() == first.size() + second.size(), "split size mismatch");
    for (std::size_t i = 0; i < first.size(); ++i) {
        require(continuous[i] == first[i], "first shard mismatch");
    }
    for (std::size_t i = 0; i < second.size(); ++i) {
        require(continuous[first.size() + i] == second[i], "second shard mismatch");
    }
    return 0;
}
