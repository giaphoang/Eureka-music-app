# Regression Report

Date: 2026-07-16

## Tests Executed

Client:

```bash
cd client
.venv/bin/python -m pytest -q
```

Result:

```text
19 passed in 0.46s
```

Server:

```bash
make server-test
```

Result:

```text
5 passed, 1 warning in 0.48s
```

Warning:

```text
StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.
```

## Functional Coverage

Verified by automated tests:

- Server catalog search, pagination, special characters, empty results, total/offset/limit.
- Server upload, download, duplicate upload, invalid upload, oversized upload, filename safety.
- Client download file write, non-zero file, interrupted download cleanup, duplicate download.
- Client playlist ordering, duplicate handling, removal, one-track playlist, restart persistence.
- Missing local file pruning and playback missing-file behavior.
- Playback queue ordering, shuffle order, loop-all next/previous, shutdown cleanup.
- Sidebar signals, player bar signals, seek feedback loop protection, queue model/view scale.

Verified by offscreen runtime checks:

- Main window launches after refactor.
- Browse page loads first catalog page.
- Downloads page holds 8,000 local rows.
- `QStackedWidget` has 4 reusable pages.
- Queue panel is hidden by default.

Not verified in this headless run:

- Audible playback through speakers.
- Human visual inspection on Ubuntu.
- Manual upload/download interaction with real dialogs.
- Hard-kill persistence after the visual refactor.

## Failures Found And Fixed

1. `scripts/memory_plateau.py` referenced the old `window.search_input`.
   - Fixed to support the refactored `window.top_bar.search_input`.
   - Added operation error handling so future harness failures exit cleanly.

2. New sidebar test expected a clicked checkable button to remain unchecked.
   - Fixed test to verify explicit active page state.

## Remaining Limitations

- Manual GUI/audio checklist is still required on the target platform.
- Native macOS/Rosetta playback crash soak remains separate from this UI refactor.
- Local refresh and playlist refresh still run synchronously; current measurements remain acceptable, but this is a known scaling risk area.
