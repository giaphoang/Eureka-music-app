from __future__ import annotations

import argparse
import csv
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class Sample:
    elapsed_s: float
    rss_mb: float
    phase: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run repeated client operations and measure RSS plateau behavior."
    )
    parser.add_argument(
        "--duration-minutes",
        type=float,
        default=15.0,
        help="Total run duration. Use 15-40 minutes for validation.",
    )
    parser.add_argument(
        "--sample-seconds",
        type=float,
        default=10.0,
        help="Seconds between RSS samples.",
    )
    parser.add_argument(
        "--operation-seconds",
        type=float,
        default=1.0,
        help="Seconds between repeated UI operations.",
    )
    parser.add_argument(
        "--plateau-window-minutes",
        type=float,
        default=5.0,
        help="Tail window used to judge whether RSS has stabilized.",
    )
    parser.add_argument(
        "--max-tail-growth-mb",
        type=float,
        default=20.0,
        help="Maximum allowed RSS growth across the tail window.",
    )
    parser.add_argument(
        "--max-tail-slope-mb-per-min",
        type=float,
        default=2.0,
        help="Maximum allowed RSS linear slope across the tail window.",
    )
    parser.add_argument(
        "--search-terms",
        default="love,blue,rock,jazz,zzzz",
        help="Comma-separated catalog search terms to cycle through.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        help="Optional CSV path for raw RSS samples.",
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Show the real desktop window instead of using Qt offscreen mode.",
    )
    parser.add_argument(
        "--skip-playback",
        action="store_true",
        help="Skip repeated QMediaPlayer queue loads.",
    )
    return parser.parse_args()


def rss_mb(pid: int) -> float:
    result = subprocess.run(
        ["ps", "-o", "rss=", "-p", str(pid)],
        check=True,
        capture_output=True,
        text=True,
    )
    return int(result.stdout.strip()) / 1024


def tail_slope_mb_per_min(samples: list[Sample]) -> float:
    if len(samples) < 2:
        return 0.0

    xs = [sample.elapsed_s / 60 for sample in samples]
    ys = [sample.rss_mb for sample in samples]
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    denominator = sum((x - x_mean) ** 2 for x in xs)
    if denominator == 0:
        return 0.0
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    return numerator / denominator


def write_csv(path: Path, samples: list[Sample]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["elapsed_s", "rss_mb", "phase"])
        for sample in samples:
            writer.writerow([f"{sample.elapsed_s:.3f}", f"{sample.rss_mb:.3f}", sample.phase])


def main() -> int:
    args = parse_args()
    if not args.visible:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide2.QtCore import QTimer
    from PySide2.QtWidgets import QApplication

    from eureka_client.config import ensure_dirs
    from eureka_client.ui.main_window import MainWindow

    ensure_dirs()

    app = QApplication(sys.argv[:1])
    window = MainWindow()
    window.player.player.setVolume(0)
    app.aboutToQuit.connect(window.shutdown)
    if args.visible:
        window.show()

    samples: list[Sample] = []
    search_terms = [term.strip() for term in args.search_terms.split(",") if term.strip()]
    if not search_terms:
        search_terms = [""]

    started_at = time.monotonic()
    deadline_s = started_at + args.duration_minutes * 60
    pid = os.getpid()
    operation_index = 0
    stop_requested = False
    finished = False
    measurement_error: str | None = None

    def elapsed_s() -> float:
        return time.monotonic() - started_at

    def current_phase() -> str:
        phases = ["refresh_local", "refresh_playlists", "search_catalog"]
        if not args.skip_playback:
            phases.append("queue_load")
        return phases[operation_index % len(phases)]

    def record_sample() -> None:
        nonlocal measurement_error
        if finished:
            return
        phase = current_phase()
        try:
            sample = Sample(elapsed_s(), rss_mb(pid), phase)
        except Exception as exc:
            measurement_error = str(exc)
            print(f"measurement_error={measurement_error}", flush=True)
            finish()
            return
        samples.append(sample)
        print(f"{sample.elapsed_s:8.1f}s rss={sample.rss_mb:8.1f}MB phase={phase}", flush=True)

    def run_operation() -> None:
        nonlocal operation_index
        if stop_requested or time.monotonic() >= deadline_s:
            finish()
            return

        phase = current_phase()
        if phase == "refresh_local":
            window.refresh_local()
        elif phase == "refresh_playlists":
            window.refresh_playlists()
        elif phase == "search_catalog":
            term = search_terms[operation_index % len(search_terms)]
            window.search_input.setText(term)
            window.search_catalog()
        elif phase == "queue_load" and window.local_tracks:
            index = operation_index % len(window.local_tracks)
            window.player.set_queue(window.local_tracks, index)
            QTimer.singleShot(250, window.player.stop)

        operation_index += 1
        QTimer.singleShot(int(args.operation_seconds * 1000), run_operation)

    def finish() -> None:
        nonlocal finished
        if finished:
            return
        finished = True
        sample_timer.stop()
        window.shutdown()
        if samples:
            final_sample = Sample(elapsed_s(), rss_mb(pid), "final")
            samples.append(final_sample)
        if args.csv:
            write_csv(args.csv, samples)

        initial = samples[0].rss_mb if samples else 0.0
        peak = max((sample.rss_mb for sample in samples), default=0.0)
        final = samples[-1].rss_mb if samples else 0.0
        tail_start = max(0.0, samples[-1].elapsed_s - args.plateau_window_minutes * 60) if samples else 0.0
        tail = [sample for sample in samples if sample.elapsed_s >= tail_start]
        tail_growth = (tail[-1].rss_mb - tail[0].rss_mb) if len(tail) >= 2 else 0.0
        tail_range = (max(sample.rss_mb for sample in tail) - min(sample.rss_mb for sample in tail)) if tail else 0.0
        slope = tail_slope_mb_per_min(tail)
        plateau_pass = (
            len(tail) >= 2
            and tail_growth <= args.max_tail_growth_mb
            and slope <= args.max_tail_slope_mb_per_min
        )

        print("", flush=True)
        print("Memory plateau summary", flush=True)
        print(f"samples={len(samples)} duration_min={elapsed_s() / 60:.2f}", flush=True)
        print(f"rss_initial_mb={initial:.1f}", flush=True)
        print(f"rss_peak_mb={peak:.1f}", flush=True)
        print(f"rss_final_mb={final:.1f}", flush=True)
        print(f"rss_growth_mb={final - initial:.1f}", flush=True)
        print(f"tail_window_min={args.plateau_window_minutes:.1f}", flush=True)
        print(f"tail_growth_mb={tail_growth:.1f}", flush=True)
        print(f"tail_range_mb={tail_range:.1f}", flush=True)
        print(f"tail_slope_mb_per_min={slope:.3f}", flush=True)
        if measurement_error:
            print(f"measurement_error={measurement_error}", flush=True)
        print(f"plateau_status={'PASS' if plateau_pass else 'PARTIAL_PASS_OR_FAIL'}", flush=True)
        if args.csv:
            print(f"csv={args.csv}", flush=True)
        app.quit()

    def request_stop(*_: object) -> None:
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    QTimer.singleShot(0, record_sample)
    sample_timer = QTimer()
    sample_timer.timeout.connect(record_sample)
    sample_timer.start(int(args.sample_seconds * 1000))
    QTimer.singleShot(0, run_operation)
    QTimer.singleShot(int(args.duration_minutes * 60 * 1000), finish)

    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
