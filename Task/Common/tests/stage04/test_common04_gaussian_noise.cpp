#include "common/noise_pool.hpp"

#include <cmath>
#include <filesystem>
#include <fstream>
#include <functional>
#include <stdexcept>
#include <string>

namespace fs = std::filesystem;

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
    const auto a = scl::common::generateStandardGaussianFrame(2026072101ULL, 0ULL, 0ULL, 16ULL);
    const auto b = scl::common::generateStandardGaussianFrame(2026072101ULL, 0ULL, 0ULL, 16ULL);
    const auto c = scl::common::generateStandardGaussianFrame(2026072101ULL, 0ULL, 1ULL, 16ULL);
    require(a == b, "Gaussian repeat mismatch");
    require(a != c, "Gaussian frame independence sample collision");
    double sum = 0.0;
    double sum2 = 0.0;
    for (std::uint64_t i = 0; i < 20000ULL; ++i) {
        const double z = scl::common::standardGaussianSample({2026072101ULL, 0ULL, i / 1000ULL, i % 1000ULL, 1ULL});
        sum += z;
        sum2 += z * z;
    }
    const double mean = sum / 20000.0;
    const double variance = sum2 / 20000.0 - mean * mean;
    require(std::fabs(mean) < 0.05, "Gaussian mean sanity failed");
    require(std::fabs(variance - 1.0) < 0.08, "Gaussian variance sanity failed");

    const fs::path dir = fs::path("Task/Common/build/stage04/cpp_noise_pool");
    fs::remove_all(dir);
    const auto manifest = scl::common::generateNoisePool(dir.string(), 2026072101ULL, 0ULL, 60ULL, 20ULL, 25ULL);
    std::ofstream(dir / "manifest.json") << scl::common::noisePoolManifestToJson(manifest);
    scl::common::NoisePoolReader reader((dir / "manifest.json").string());
    require(reader.noisePoolId() == manifest.noisePoolId, "noisePoolId mismatch");
    require(reader.readFramePrefix(0ULL, 3ULL).size() == 3U, "first frame prefix mismatch");
    require(reader.readFramePrefix(24ULL, 20ULL).size() == 20U, "shard end prefix mismatch");
    require(reader.readFramePrefix(25ULL, 5ULL).size() == 5U, "shard boundary prefix mismatch");
    require(reader.readFramePrefix(59ULL, 1ULL).size() == 1U, "last frame prefix mismatch");
    const auto header = scl::common::readNoiseShardHeader((dir / manifest.shards.front().fileName).string());
    require(header.headerVersion == scl::common::kNoiseShardHeaderVersion, "header version mismatch");
    requireThrows("prefix out of range", [&] { (void)reader.readFramePrefix(0ULL, 21ULL); });
    requireThrows("frame out of range", [&] { (void)reader.readFramePrefix(60ULL, 1ULL); });
    return 0;
}
