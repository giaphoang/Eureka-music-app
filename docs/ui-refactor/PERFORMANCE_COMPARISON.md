# Performance Comparison

Date: 2026-07-16

Data set:

```text
server catalog rows=8003
local downloaded rows=8000
EUREKA_DATA_DIR=/tmp/eureka-ui-baseline
```

The local baseline store references read-only FMA source files to avoid copying the full dataset on a disk-full development machine.

## Startup

Method:

- `QT_QPA_PLATFORM=offscreen`
- Real `QApplication`
- Real `MainWindow`
- Backend running on `localhost:8000`
- Complete when:
  - main window visible;
  - zero-delay timer fired;
  - local rows loaded;
  - first catalog page loaded.

### Baseline

```text
run=1 elapsed=0.590127 rss_mb=100.3
run=2 elapsed=0.198235 rss_mb=101.6
run=3 elapsed=0.212392 rss_mb=102.0
run=4 elapsed=0.194357 rss_mb=101.6
run=5 elapsed=0.194776 rss_mb=100.9

startup_min=0.194357
startup_median=0.198235
startup_max=0.590127
rss_median_mb=101.6
```

### Refactored

```text
run=1 elapsed=0.226974 rss_mb=106.4
run=2 elapsed=0.222861 rss_mb=107.1
run=3 elapsed=0.223250 rss_mb=106.7
run=4 elapsed=0.226284 rss_mb=106.9
run=5 elapsed=0.236121 rss_mb=107.2

startup_min=0.222861
startup_median=0.226284
startup_max=0.236121
rss_median_mb=106.9
```

Result:

```text
startup_under_10s=VERIFIED_PASS
startup_regression=acceptable; refactored max remains far below 10s
rss_startup_delta=about +5.3 MB median
```

## Navigation And Refresh Memory Check

Command pattern:

```text
100 page switches
queue toggled every 5 switches
50 local refreshes
50 playlist refreshes
```

Result:

```text
initial_rss_mb=105.6
after_100_navigation_mb=142.5
after_50_refresh_mb=152.4
stack_count=4
sidebar_buttons=4
```

Interpretation:

- Pages are not recreated during navigation.
- RSS increases during repeated operations.
- This short run does not prove an unbounded leak.
- The long plateau run below is the authoritative memory check.

## 15-Minute Memory Plateau

Command:

```bash
cd client
EUREKA_DATA_DIR=/tmp/eureka-ui-baseline \
EUREKA_API_URL=http://localhost:8000 \
.venv/bin/python scripts/memory_plateau.py \
  --duration-minutes 15 \
  --sample-seconds 30 \
  --operation-seconds 1 \
  --csv ../docs/ui-refactor/memory-plateau-refactor.csv
```

Summary:

```text
samples=31
duration_min=15.01
rss_initial_mb=98.4
rss_peak_mb=161.7
rss_final_mb=127.6
rss_growth_mb=29.2
tail_window_min=5.0
tail_growth_mb=-30.2
tail_range_mb=54.8
tail_slope_mb_per_min=-6.585
plateau_status=PASS
csv=../docs/ui-refactor/memory-plateau-refactor.csv
```

Result:

```text
memory_plateau=VERIFIED_PASS
```

The tail window has a negative slope. The wide tail range reflects RSS dropping late in the run rather than steadily increasing.
