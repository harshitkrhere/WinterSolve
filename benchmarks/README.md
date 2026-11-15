# Repository benchmark

Run `python benchmarks/repository_benchmark.py --sizes 1000 10000 50000 100000`
from the repository root. The script creates temporary repositories and removes
them after each case. Use `--python-source --bandit` to time Bandit separately.
Use `--total-only` when only warm full-report time and peak traced allocations
are needed. Set `PYTHONPATH` to another checkout's `src` directory to compare
revisions without changing this checkout.

## Measurements, 14 November 2026

Windows 11 (build 26320), AMD64 Family 25 Model 80, Python 3.14.7. Storage
type and antivirus state were not measured. Each fixture has 40% source, tests,
config, or docs; 30% `.next-recovery-e2e` generated files; and 30%
`node_modules` files. The baseline was commit `b390e07`; the revised run used
the working tree. Bandit was disabled for the main comparison.

| Requested files | Baseline discovered | Revised discovered | Baseline warm `brain` | Revised warm `brain` | Baseline peak traced allocations | Revised peak traced allocations |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1,000 | 702 | 402 | 0.373 s | 0.241 s | 1.08 MB | 3.25 MB |
| 10,000 | 7,002 | 4,002 | 3.464 s | 2.048 s | 10.70 MB | 7.96 MB |
| 50,000 | 35,002 | 20,002 | 17.571 s | 7.621 s | 53.81 MB | 29.95 MB |
| 100,000 | 70,002 | 40,002 | 35.974 s | 18.692 s | 105.77 MB | 57.84 MB |

The 50,000 and 100,000 baseline measurements used `--total-only`; both
revisions' full-report times are after a warming pass. Peak memory is from
`tracemalloc` and excludes interpreter and native allocations. Fixture setup
and cleanup are excluded from the times. On the 100,000 file revised run,
discovery took 7.613 s, metadata analysis 0.285 s, architecture analysis
0.031 s, and JSON rendering under 0.001 s. The first standalone built-in
security pass took 56.575 s with eight readers, down from 268.657 s with
serial reads. At 50,000 files, the cold pass took 21.018 s versus 115.495 s.
These cold passes are sensitive to filesystem cache and antivirus behavior and
should not be treated as stable throughput claims.

With `--python-source --bandit` on a 1,000 file fixture, Bandit alone took
0.586 s on the baseline and 1.147-3.367 s across two revised runs. The full
warm report took 0.937 s on the baseline and 1.347-1.419 s on the revised
code. Bandit startup and Windows caching varied substantially; this case is
too small to predict Bandit cost on large Python repositories. The revised
Bandit pass has a
120-second total limit and reports incomplete coverage if it expires.

`cProfile` on a serial-read revised 1,000 file fixture attributed 2.110 s of a 2.427 s
run to Windows `nt.open` for 405 file opens; security pattern evaluation took
about 0.024 s. File-open latency is the main measured bottleneck. The
benchmark does not simulate a concurrently changing repository, network
storage, or an SSD versus HDD comparison.
