#include "bch_block/bch_block.hpp"
#include <fstream>
#include <iostream>

int main(int argc, char** argv) {
    if (argc != 2) { std::cerr << "usage: export_bch_block_reference output.csv\n"; return 2; }
    std::ofstream out(argv[1]); if (!out) return 3;
    out << "caseName,fieldDegree,primitivePolynomial,generatorPolynomial,generatorDegree,correctionCapability,shorteningLength,shortenedN,shortenedK\n";
    for (const auto& p : {scl::bch::block::makeB200Profile(), scl::bch::block::makeB300Profile()}) {
        out << p.caseName << ',' << p.fieldDegree << ',' << p.primitivePolynomial << ','
            << scl::bch::block::bitsToString(p.generatorPolynomial) << ',' << p.generatorPolynomial.size()-1U << ','
            << p.correctionCapability << ',' << p.shorteningLength << ',' << p.motherN-p.shorteningLength << ',' << p.payloadLength << '\n';
    }
}
