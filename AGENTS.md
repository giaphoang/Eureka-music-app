# AGENTS.md — Eureka Music App

## Purpose

This file defines the permanent operating rules for coding agents working in this repository.

Task-specific requirements, benchmarks, test cases, and deliverables will be provided separately in the current prompt.

## Project overview

Eureka Music App is a local music-management system designed to run on Ubuntu.

It consists of:

* A FastAPI server backed by PostgreSQL.
* A Python desktop client built with PySide2 5.15.x.
* SQLite-based client persistence where appropriate.
* Docker and Docker Compose for running the server.

The server is the source of truth for the shared music catalog and audio files. The client owns downloaded-track state and playlists.

The desktop client allows users to:

* Browse and search the server catalog.
* Download tracks.
* Browse and play downloaded tracks locally.
* Play, pause, continue, stop, and seek within a track.
* Create playlists.
* Reorder playlist tracks manually.
* Use shuffle and loop playback.
* Upload local tracks to the server.

The project uses the FMA Small dataset. Both the server and client provide seed scripts that accept the unzipped FMA parent directory as a positional CLI argument.

The application must remain usable with approximately 8,000 tracks. Important quality goals are:

* Startup below 10 seconds on a typical laptop.
* No UI freezing during long-running operations.
* Persistence after abrupt process termination.
* Stable memory during repeated use.
* Clear and recoverable error handling.

The project does not require:

* Authentication.
* Cloud deployment.
* Spotify, YouTube, or other music-service integrations.
* Cross-platform support beyond the required Ubuntu target.
* Pixel-perfect visual design.
* Social features, DRM, lyrics, podcasts, or unrelated functionality.

Detailed architecture belongs in `DESIGN.md`. Installation and execution instructions belong in the repository README files. Task-specific goals and acceptance criteria must be provided in the current coding-agent prompt.

## Instruction priority

Follow instructions in this order:

1. Current human instructions.
2. Safety and data-preservation rules in this file.
3. Assignment requirements.
4. Existing tests and executable configuration.
5. Current implementation.
6. Repository documentation and conventions.

When code, tests, and documentation conflict, record the conflict instead of silently guessing.

## Project invariants

Do not change these constraints without explicit human approval:

* Server: FastAPI, PostgreSQL, Docker, and Docker Compose.
* Desktop client: Python 3 and PySide2 5.15.x.
* Client persistence: SQLite where appropriate.
* Client runs from a Python virtual environment.
* Server is the source of truth for the music catalog.
* No Spotify, YouTube, or third-party music provider dependency.
* Both server and client provide FMA seed scripts.
* Seed scripts accept the unzipped FMA parent directory as a positional argument.
* The application must remain compatible with the assignment requirements.

Do not add unrelated features such as authentication, cloud deployment, DRM, social functionality, or bonus functionality unless explicitly requested.

## Repository and data safety

Never commit:

* FMA datasets or archives.
* MP3, WAV, FLAC, OGG, or M4A files.
* Virtual environments.
* Python caches.
* Test caches.
* Local SQLite databases.
* SQLite WAL or SHM files.
* Docker runtime data.
* Temporary download or upload files.
* Secrets, credentials, or API keys.
* Large generated logs unless explicitly requested.

Treat the FMA source directory as read-only.

Never delete or modify the source dataset.

Do not use destructive operations such as:

* `git reset --hard`
* `git clean -fd`
* history rewriting
* force-pushing
* deleting branches or tags
* `docker compose down -v`

Do not push or merge without explicit human authorization.

## Preflight

Before modifying code:

1. Verify the repository root.
2. Run:

   * `git status --short`
   * `git branch --show-current`
   * `git log -5 --oneline`
3. Identify existing human changes.
4. Discover the actual repository structure.
5. Read the relevant implementation, tests, and documentation.
6. Verify that referenced files and commands exist.

Do not create a file merely because an old prompt or document mentions it.

## Evidence and uncertainty

Never invent:

* File contents.
* Command output.
* Test results.
* Test counts.
* Measurements.
* Commit hashes.
* API responses.
* Platform compatibility.
* Manual verification results.

Classify claims as:

* `OBSERVED`: directly read from code, configuration, logs, or repository state.
* `VERIFIED_PASS`: confirmed by executed verification.
* `VERIFIED_FAIL`: executed verification failed.
* `INFERRED`: supported by evidence but not directly confirmed.
* `PROPOSED`: a recommended future change.
* `BLOCKED`: required capability, access, data, or environment is unavailable.
* `NOT_VERIFIED`: verification was not completed.

Never present `INFERRED`, `PROPOSED`, `BLOCKED`, or `NOT_VERIFIED` as verified success.

## Standard workflow

For every scoped task:

1. **Inspect** — understand the current implementation and behavior.
2. **Baseline** — reproduce and record the current result before changing code.
3. **Plan** — identify the smallest change, affected files, risks, and acceptance criteria.
4. **Implement** — make only the approved, scoped change.
5. **Target-test** — run the narrowest relevant verification.
6. **Regression-test** — run the relevant component suite.
7. **Record** — preserve before-and-after evidence.
8. **Review** — inspect the Git diff and remaining risks.

Run the full suite after major cross-component changes and before final completion, not after every trivial edit.

## Remediation rules

Fix only:

* Reproduced defects.
* Missing requirements.
* Verified reliability problems.
* Verified performance problems.
* Documentation that conflicts with actual behavior.

Use the smallest coherent fix.

Avoid unrelated refactoring and formatting.

Add a regression test when practical.

Preserve the original baseline result after remediation so reports distinguish:

* Baseline status.
* Change made.
* Final status.

## Human approval required

Stop and request human approval before:

* Changing architecture.
* Changing database schemas or persistence formats.
* Adding or upgrading significant dependencies.
* Changing public API contracts.
* Removing user data.
* Expanding beyond the current task scope.
* Performing destructive or irreversible operations.
* Accepting a major trade-off between requirements.
* Pushing, merging, or rewriting Git history.

Routine investigation, scoped implementation, testing, and evidence collection may continue without approval when they remain inside the current prompt's boundaries.

## Verification

Do not claim success based only on code inspection.

A requirement passes only when:

* The required verification was executed.
* The observed behavior matches the acceptance criteria.
* Evidence was recorded.
* Relevant regression tests pass.
* No known regression remains in the tested scope.

For GUI, audio, platform, or hardware behavior that cannot be tested automatically:

* mark it `BLOCKED` or `NOT_VERIFIED`;
* provide exact manual verification steps;
* do not simulate or infer success.

## Git publishing policy

By default, agents may modify files and run tests, but must not commit, push, merge, or open a pull request unless the current human prompt explicitly authorizes it.

Use three permission levels:

* Default: edit and test only.
* "Commit this change": commit locally, but do not push.
* "Publish this change": commit, push the approved branch, and optionally open a draft pull request.

When publishing is authorized:

* Preserve unrelated human changes.
* Run required tests before committing.
* Review `git diff` and staged files.
* Create logical commits with descriptive messages.
* Never force-push, rewrite history, rebase shared branches, or amend human commits.
* Push only to the authorized branch.
* Never merge automatically unless explicitly requested.

AGENTS.md defines whether agents are allowed to publish. The current human prompt defines whether permission is granted now. A dedicated skill or task prompt should define the step-by-step publishing procedure. Do not put the Git publishing procedure in `SKILLS.md`; this repository's `SKILLS.md` is for describing engineering skills used in the project.

## Completion handoff

At the end of each task, report:

* Objective.
* Baseline result.
* Files changed.
* Commands executed.
* Exact results.
* Evidence locations.
* Final status.
* Remaining uncertainty.
* Human decision or action required.
