#include "bch_simulation/bch_awgn_simulation.hpp"

#include <filesystem>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>

namespace fs = std::filesystem;

namespace {

std::map<std::string, std::string> parse(int argc, char** argv) {
    std::map<std::string, std::string> values;
    for (int i = 1; i < argc; ++i) {
        const std::string key(argv[i]);
        if (key == "--progress" || key == "--no-progress" || key == "--detail" || key == "--resume") {
            values[key] = "1";
        } else {
            if (key.rfind("--", 0U) != 0U || i + 1 >= argc) throw std::invalid_argument("invalid runner arguments");
            values[key] = argv[++i];
        }
    }
    return values;
}

std::string required(const std::map<std::string, std::string>& values, const std::string& key) {
    const auto found = values.find(key);
    if (found == values.end()) throw std::invalid_argument("missing argument " + key);
    return found->second;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const auto args = parse(argc, argv);
        scl::bch::simulation::AwgnPointConfig config;
        config.stage = required(args, "--stage");
        config.caseId = scl::bch::simulation::bchSimulationCase(required(args, "--case")).id;
        config.ebN0Db = std::stod(required(args, "--ebn0-db"));
        config.snrIndex = static_cast<std::size_t>(std::stoull(required(args, "--snr-index")));
        config.frameStart = static_cast<std::uint64_t>(std::stoull(required(args, "--frame-start")));
        config.frameCount = static_cast<std::uint64_t>(std::stoull(required(args, "--frame-count")));
        config.logicalFrameCount = args.count("--logical-frame-count") ? static_cast<std::uint64_t>(std::stoull(args.at("--logical-frame-count"))) : config.frameCount;
        config.globalSeed = static_cast<std::uint64_t>(std::stoull(required(args, "--global-seed")));
        config.framePoolManifest = required(args, "--frame-pool-manifest");
        config.outputDirectory = required(args, "--output-dir");
        config.progress = args.count("--no-progress") == 0U;
        if (args.count("--progress") != 0U) config.progress = true;
        if (args.count("--progress-refresh-seconds") != 0U) {
            config.progressRefreshSeconds = std::stod(args.at("--progress-refresh-seconds"));
        }
        config.writeFrameDetail = args.count("--detail") != 0U;
        if (args.count("--min-frames") != 0U || args.count("--target-frame-errors") != 0U || args.count("--max-frames") != 0U) {
            config.adaptiveStop = true;
            config.minFrames = static_cast<std::uint64_t>(std::stoull(required(args, "--min-frames")));
            config.targetFrameErrors = static_cast<std::uint64_t>(std::stoull(required(args, "--target-frame-errors")));
            config.maxFrames = static_cast<std::uint64_t>(std::stoull(required(args, "--max-frames")));
        }
        if (args.count("--checkpoint") != 0U) config.checkpointPath = args.at("--checkpoint");
        if (args.count("--checkpoint-interval") != 0U) config.checkpointInterval = static_cast<std::uint64_t>(std::stoull(args.at("--checkpoint-interval")));
        config.resume = args.count("--resume") != 0U;
        if (args.count("--interrupt-after-frames") != 0U) config.interruptAfterFrames = static_cast<std::uint64_t>(std::stoull(args.at("--interrupt-after-frames")));
        if (args.count("--shard-index") != 0U) config.shardIndex = static_cast<std::uint64_t>(std::stoull(args.at("--shard-index")));
        if (args.count("--shard-count") != 0U) config.shardCount = static_cast<std::uint64_t>(std::stoull(args.at("--shard-count")));
        const auto result = scl::bch::simulation::runAwgnPoint(config);
        scl::bch::simulation::writeAwgnPointSummary(result, (fs::path(config.outputDirectory) / "summary.csv").string());
        std::cout << "PASS_" << config.stage << '_' << scl::bch::simulation::bchSimulationCase(config.caseId).caseName << '_'
                  << config.snrIndex << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BLOCKED_BCH_AWGN_RUNNER: " << error.what() << '\n';
        return 1;
    }
}
