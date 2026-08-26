# Analysis-specific RT feature definitions V1

`behavior_longitudinal_v1` and `behavior_baseline_v2`/C2B both expose RT-related fields, but the same-looking names do not imply one universal feature definition.

| analysis surface | source rule | status |
|---|---|---|
| `behavior_longitudinal_v1` | `valid_go_rt`: Go trials only, a response is present, and RT is at least 150 ms; probe-window summaries are derived from these valid Go RT values | frozen historical definition |
| `behavior_baseline_v2` | `b_rt_*`: non-null RT values in the pre-probe window, without the longitudinal `Go + response + RT >= 150 ms` filter | frozen analysis-specific definition |
| C2B behavior features | reuses the baseline-style `b_rt_*` construction inside the C2B producer | frozen analysis-specific definition |

The two surfaces must not be described as completely identical unified RT features. This note records the distinction without changing or rerunning accepted historical results. Any future unification requires a new explicitly versioned pipeline and rerun of the affected analyses.
