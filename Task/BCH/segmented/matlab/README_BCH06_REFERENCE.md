# BCH-06 MATLAB independent reference

The MATLAB reference uses row-vector, left-most-highest-degree GF(2) long division with generator `[1 0 0 1 1]`. It does not read C++ exports as algorithm input. CSV is ASCII/UTF-8 with fixed `0`/`1` bit strings, 0-based error positions, and uppercase decoder statuses.
