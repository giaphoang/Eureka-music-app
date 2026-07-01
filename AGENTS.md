# AI Agent Instructions

## Product constraint

Implement only the assignment scope: server-owned catalog/audio, desktop browsing/downloading/local playback/playlists/upload, FMA data, Docker Compose, PySide2, Postgres, and SQLite.

## Engineering rules

- Never execute blocking HTTP or file-copy work on the Qt UI thread.
- Never write directly to a final audio filename; use a temporary file and atomic rename.
- Preserve user data across SIGKILL and container recreation.
- Use Python 3.10 because PySide2 does not support Python 3.11+.
- Keep platform-specific code isolated; final behavior must be verified on Ubuntu.
- Add a test or a reproducible manual verification step for each feature.

## AI usage record

When AI assists with a change, record:

1. The design question or prompt.
2. Alternatives considered.
3. The selected trade-off and why.
4. Human verification performed.
5. Any generated code that was materially rewritten.
