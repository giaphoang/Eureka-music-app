# Manual Test Results

Date: 2026-07-16

## Automated And Offscreen Checks Completed

- Client tests: `19 passed in 0.46s`
- Server tests: `5 passed, 1 warning in 0.48s`
- Offscreen launch: `downloads=8000`, `catalog=500`, `stack_count=4`, `queue_visible=False`
- Refactored screenshot captured.
- 15-minute memory plateau: `plateau_status=PASS`

## Manual Checklist Status

These checks still require a human run on macOS or Ubuntu with audio output:

### Catalog

```text
Browse server tracks: NOT_VERIFIED manually after refactor
Search: NOT_VERIFIED manually after refactor
Pagination: NOT_VERIFIED manually after refactor
Empty results: NOT_VERIFIED manually after refactor
Backend unavailable behavior: NOT_VERIFIED manually after refactor
```

### Download

```text
Download one track: NOT_VERIFIED manually after refactor
Download multiple tracks: NOT_VERIFIED manually after refactor
Duplicate download: NOT_VERIFIED manually after refactor
Failed download: NOT_VERIFIED manually after refactor
Switch pages during download: NOT_VERIFIED manually after refactor
```

### Playback

```text
Play: NOT_VERIFIED manually after refactor
Pause: NOT_VERIFIED manually after refactor
Continue: NOT_VERIFIED manually after refactor
Stop: NOT_VERIFIED manually after refactor
Seek: NOT_VERIFIED manually after refactor
Previous: NOT_VERIFIED manually after refactor
Next: NOT_VERIFIED manually after refactor
Missing file: NOT_VERIFIED manually after refactor
Playback error: NOT_VERIFIED manually after refactor
Continue using UI while playing: NOT_VERIFIED manually after refactor
```

### Playlists

```text
Create: NOT_VERIFIED manually after refactor
Add: NOT_VERIFIED manually after refactor
Remove: NOT_VERIFIED manually after refactor
Reorder: NOT_VERIFIED manually after refactor
Shuffle: NOT_VERIFIED manually after refactor
Loop off: NOT_VERIFIED manually after refactor
Loop one: NOT_VERIFIED manually after refactor
Loop all: NOT_VERIFIED manually after refactor
Empty playlist: NOT_VERIFIED manually after refactor
One-track playlist: NOT_VERIFIED manually after refactor
Restart and verify persistence: NOT_VERIFIED manually after refactor
```

### Upload

```text
Upload valid FMA MP3: NOT_VERIFIED manually after refactor
Upload error: NOT_VERIFIED manually after refactor
Continue using UI during upload: NOT_VERIFIED manually after refactor
Uploaded track appears in catalog: NOT_VERIFIED manually after refactor
```

### Persistence

```text
Hard-kill client: NOT_VERIFIED manually after refactor
Restart: NOT_VERIFIED manually after refactor
Completed downloads: NOT_VERIFIED manually after refactor
Playlist order: NOT_VERIFIED manually after refactor
Incomplete download is not valid: NOT_VERIFIED manually after refactor
```

### Scale

```text
Full 8,000 server tracks: VERIFIED_PASS by backend count and startup harness
Full 8,000 client tracks: VERIFIED_PASS by startup harness
Startup under 10 seconds: VERIFIED_PASS
Search responsive: VERIFIED_PASS by startup/search worker behavior and tests; manual check still recommended
Memory stable: VERIFIED_PASS by 15-minute plateau harness
```
