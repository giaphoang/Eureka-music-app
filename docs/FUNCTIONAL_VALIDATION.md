# Functional Validation

Date: 2026-07-16

## Automated verification results

```bash
cd client
.venv/bin/python -m pytest -q
# 10 passed in 0.33s
```

```bash
cd ..
docker compose build api
docker compose run --rm api python -m pytest -q
# 5 passed, 1 warning in 0.55s
```

The server warning is from FastAPI/Starlette test client compatibility:
`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated`.

## Coverage matrix

| Area | Requirement | Status | Verification | Evidence | Defect or risk | Required fix |
| --- | --- | --- | --- | --- | --- | --- |
| Server catalog | List tracks | VERIFIED_PASS | API test creates tracks and lists them | `server/tests/test_tracks.py::test_catalog_search_pagination_and_metadata` | None observed | None |
| Server catalog | Paginate tracks | VERIFIED_PASS | API test requests `offset=1&limit=2` | `server/tests/test_tracks.py::test_catalog_search_pagination_and_metadata` | None observed | None |
| Server catalog | Search by title | VERIFIED_PASS | API test searches `Alpha` | `server/tests/test_tracks.py::test_catalog_search_pagination_and_metadata` | None observed | None |
| Server catalog | Search by artist | VERIFIED_PASS | API test searches `Artist/Slash` | `server/tests/test_tracks.py::test_catalog_search_pagination_and_metadata` | None observed | None |
| Server catalog | Search by album | VERIFIED_PASS | API test searches `Odd [Album]` | `server/tests/test_tracks.py::test_catalog_search_pagination_and_metadata` | None observed | None |
| Server catalog | Empty search results | VERIFIED_PASS | API test expects empty page for missing term | `server/tests/test_tracks.py::test_catalog_search_pagination_and_metadata` | None observed | None |
| Server catalog | Special characters | VERIFIED_PASS | API test searches `C++ & Jazz?` | `server/tests/test_tracks.py::test_catalog_search_pagination_and_metadata` | None observed | None |
| Server catalog | Correct `total`, `offset`, `limit` | VERIFIED_PASS | API test asserts response metadata | `server/tests/test_tracks.py::test_catalog_search_pagination_and_metadata` | None observed | None |
| Download | Download a valid track | VERIFIED_PASS | Server API download and client API fake stream tests | `server/tests/test_tracks.py::test_upload_list_and_download`, `client/test_api.py` | None observed | None |
| Download | Resulting file exists | VERIFIED_PASS | Client download writes expected file | `client/test_api.py::test_download_track_writes_file_and_progress` | None observed | None |
| Download | File size is non-zero | VERIFIED_PASS | Server and client tests assert file/content size | `server/tests/test_tracks.py`, `client/test_api.py` | None observed | None |
| Download | Downloaded track can be played locally | NOT_VERIFIED | Requires real audio backend and GUI/manual playback | Manual steps below | Audio decode/playback not proven by automated tests | Run manual playback validation |
| Download | Interrupted downloads do not appear completed | VERIFIED_PASS | Fake stream raises mid-transfer; no final file remains | `client/test_api.py::test_interrupted_download_does_not_leave_complete_or_part_file` | None observed | None |
| Download | `.part` files cleaned up or recoverable | VERIFIED_PASS | Tests assert no `.part` after success/failure | `client/test_api.py`, `server/tests/test_tracks.py::test_invalid_oversized_upload_and_path_safety` | None observed | None |
| Download | Duplicate download behavior | VERIFIED_PASS | Same track downloads to same final path safely | `client/test_api.py::test_duplicate_download_reuses_final_path_safely` | Behavior is overwrite/re-download, not skip | Document or add explicit UI copy if desired |
| Upload | Upload a valid FMA MP3 | NOT_VERIFIED | Automated test uses representative MP3 bytes, not a real FMA MP3 | Manual steps below | Real FMA audio upload not executed | Run manual FMA upload validation |
| Upload | Supply title, artist, album, genre, tags | VERIFIED_PASS | API test asserts metadata round trip | `server/tests/test_tracks.py::test_upload_metadata_download_and_duplicate_cleanup` | Client UI currently does not expose `tags` field | Add tags input to client upload form if UI must supply tags |
| Upload | New track appears in server catalog | VERIFIED_PASS | API test searches uploaded title | `server/tests/test_tracks.py::test_upload_metadata_download_and_duplicate_cleanup` | None observed | None |
| Upload | Uploaded track can be downloaded | VERIFIED_PASS | API test downloads uploaded content | `server/tests/test_tracks.py::test_upload_metadata_download_and_duplicate_cleanup` | None observed | None |
| Upload | Invalid or oversized uploads get clear errors | VERIFIED_PASS | API test checks 415 and 413 details | `server/tests/test_tracks.py::test_invalid_oversized_upload_and_path_safety` | None observed | None |
| Upload | Failed DB insert leaves no orphan final audio | VERIFIED_PASS | Duplicate checksum causes 409 and file set is unchanged | `server/tests/test_tracks.py::test_upload_metadata_download_and_duplicate_cleanup` | None observed | None |
| Upload | Filenames cannot escape audio directory | VERIFIED_PASS | API test uploads `../../escaped.mp3` and checks sanitized final path | `server/tests/test_tracks.py::test_invalid_oversized_upload_and_path_safety` | None observed | None |
| Local playback | Play downloaded track | NOT_VERIFIED | Requires real audio backend and GUI/manual playback | Manual steps below | Not proven in automation | Run manual playback validation |
| Local playback | Pause | NOT_VERIFIED | Requires real audio backend and GUI/manual playback | Manual steps below | Not proven in automation | Run manual playback validation |
| Local playback | Continue from paused position | NOT_VERIFIED | Requires real audio backend and GUI/manual playback | Manual steps below | Not proven in automation | Run manual playback validation |
| Local playback | Stop | NOT_VERIFIED | Requires real audio backend and GUI/manual playback | Manual steps below | Not proven in automation | Run manual playback validation |
| Local playback | Seek forward/back/near end | NOT_VERIFIED | Requires real audio backend and GUI/manual playback | Manual steps below | Not proven in automation | Run manual playback validation |
| Local playback | Display current position and duration | NOT_VERIFIED | Requires real audio backend and GUI/manual playback | Manual steps below | Not proven in automation | Run manual playback validation |
| Local playback | Missing local file does not crash | VERIFIED_PASS | Isolated controller test filters missing files | `client/test_player.py::test_set_queue_with_only_missing_files_stops_without_crashing` | UI message for skipped missing file is not verified | Add user-visible missing-file message |
| Local playback | Playback errors visible | NOT_VERIFIED | Requires forcing real `QMediaPlayer` error in GUI | Manual steps below | Not proven in automation | Run manual playback error validation |
| Local playback | UI remains responsive during playback | NOT_VERIFIED | Requires live GUI observation | Manual steps below | Not proven in automation | Run manual responsiveness validation |
| Playlists | Create playlist | VERIFIED_PASS | SQLite test creates playlists | `client/test_db.py` | None observed | None |
| Playlists | Add downloaded tracks | VERIFIED_PASS | SQLite tests add tracks to playlist | `client/test_db.py` | None observed | None |
| Playlists | Duplicate additions handled | VERIFIED_PASS | Duplicate add is ignored | `client/test_db.py::test_playlist_duplicate_remove_and_restart_persistence` | No UI feedback for duplicate add verified | Add/verify user-visible duplicate feedback if required |
| Playlists | Remove track | VERIFIED_PASS | SQLite test removes and normalizes order | `client/test_db.py::test_playlist_duplicate_remove_and_restart_persistence` | None observed | None |
| Playlists | Move track up | VERIFIED_PASS | Existing DB test moves track up | `client/test_db.py::test_playlist_order` | None observed | None |
| Playlists | Move track down | VERIFIED_PASS | DB test moves track down via positive delta | `client/test_db.py::test_playlist_duplicate_remove_and_restart_persistence` | None observed | None |
| Playlists | Preserve manual order after restart | VERIFIED_PASS | Reopens DB and checks order | `client/test_db.py::test_playlist_duplicate_remove_and_restart_persistence` | None observed | None |
| Playlists | Play playlist in manual order | VERIFIED_PASS partial | Controller order test verifies manual next/previous order without real audio | `client/test_player.py::test_manual_order_next_previous_and_loop_all` | GUI/audio playback not verified | Run manual playlist playback validation |
| Playlists | Shuffle | VERIFIED_PASS partial | Controller test verifies shuffle order contains each track once | `client/test_player.py::test_shuffle_order_contains_each_track_once` | Random playback behavior not observed in GUI | Run manual shuffle validation |
| Playlists | Loop off | VERIFIED_PASS partial | Controller stops at end when loop is off | `client/test_player.py::test_manual_order_next_previous_and_loop_all` | End-of-media signal not verified with real audio | Run manual loop validation |
| Playlists | Loop one | NOT_VERIFIED | Requires real end-of-media event or deeper Qt mocking | Manual steps below | Not proven in automation | Add controller unit seam or Qt integration test |
| Playlists | Loop all | VERIFIED_PASS partial | Controller wraps from end to start | `client/test_player.py::test_manual_order_next_previous_and_loop_all` | End-of-media signal not verified with real audio | Run manual loop validation |
| Playlists | Previous and next | VERIFIED_PASS partial | Controller next/previous tested | `client/test_player.py::test_manual_order_next_previous_and_loop_all` | GUI button behavior not verified | Run manual playlist validation |
| Playlists | Empty playlist | VERIFIED_PASS | DB test verifies empty playlist track list | `client/test_db.py::test_empty_and_one_track_playlist` | UI play action not verified | Run manual empty-playlist validation |
| Playlists | One-track playlist | VERIFIED_PASS | DB test verifies move no-op on one item | `client/test_db.py::test_empty_and_one_track_playlist` | Audio/UI behavior not verified | Run manual one-track validation |
| Playlists | Missing local audio referenced by playlist | VERIFIED_PASS partial | Controller skips missing local files without crash | `client/test_player.py` | UI message not verified | Add/verify visible skipped-file message |
| User experience | Buttons disabled when action invalid | OBSERVED risk | UI code keeps several action buttons enabled and shows messages instead | `client/eureka_client/ui/main_window.py` | Requirement may fail for invalid selection states | Disable invalid actions based on selection/state |
| User experience | Long operations provide progress/status | OBSERVED partial | Download status/progress and upload progress exist; catalog status exists | `client/eureka_client/ui/main_window.py` | Upload progress is indeterminate only; seed has CLI output only | Improve determinate upload/seed progress if required |
| User experience | Errors shown to user | OBSERVED partial | Worker errors connect to `QMessageBox`; catalog failure uses status bar | `client/eureka_client/ui/main_window.py` | Not manually verified | Run manual error validation |
| User experience | Search/download/upload/seed do not freeze Qt loop | OBSERVED partial | Search/download/upload use `QThreadPool`; seed is CLI script | `client/eureka_client/ui/main_window.py`, `client/eureka_client/workers/task.py` | Live UI responsiveness not measured | Run manual responsiveness test or pytest-qt test |
| User experience | Interface understandable after startup | NOT_VERIFIED | Requires human GUI review | Manual steps below | Not proven | Run manual UX review |
| User experience | Table and playlist selection behavior | NOT_VERIFIED | Requires GUI interaction | Manual steps below | Not proven | Run manual selection validation |
| User experience | Resizing keeps controls accessible | NOT_VERIFIED | Requires GUI interaction | Manual steps below | Not proven | Run manual resize validation |

## Manual validation steps

Use real FMA Small data and at least one downloaded/uploaded MP3. Record the exact platform, Python architecture, backend status, and dataset path before starting.

### Setup

1. Start the server:

   ```bash
   docker compose up --build -d
   curl http://localhost:8000/health
   ```

2. Seed the server with at least 100 tracks:

   ```bash
   docker compose run --rm \
     -v "$HOME/Documents/FMA:/dataset/fma:ro" \
     api python -m scripts.seed_fma /dataset/fma --limit 100
   ```

3. Start the client:

   ```bash
   cd client
   source .venv/bin/activate
   python -m eureka_client.app
   ```

Observed result in this pass: NOT_VERIFIED. These steps were not executed in a live GUI/audio session.

### Download and playback

1. In **Server catalog**, select a seeded track.
2. Click **Download selected**.
3. Verify a progress/status message appears.
4. Open **Downloaded**.
5. Select the downloaded track and click **Play selected**.
6. Verify audible playback begins and **Now playing** shows the selected title/artist.
7. Verify the local downloaded file exists under the configured client data directory and has non-zero size.
8. Pause playback.
9. Wait two seconds and confirm the position does not advance.
10. Click play again and confirm playback continues from the paused position.
11. Seek forward, seek backward, and seek near the end.
12. Verify the current position and duration label update coherently.
13. Click **Stop** and confirm playback stops.

Observed result in this pass: NOT_VERIFIED.

### Playback errors and missing files

1. Download a track.
2. Stop playback.
3. Rename or delete the local audio file outside the app.
4. Click **Refresh** in **Downloaded**.
5. Select the missing track and click **Play selected**.
6. Verify the app does not crash.
7. Verify any playback error is visible in the UI, not only in the terminal.

Observed result in this pass: NOT_VERIFIED. Automated controller tests verify no crash for missing-file queue filtering, but not the visible UI message.

### Upload real FMA MP3

1. Open **Upload**.
2. Choose an MP3 from `$HOME/Documents/FMA/fma_small`.
3. Enter title, artist, album, and genre.
4. Upload the track.
5. Search for the title in **Server catalog**.
6. Download the uploaded track.
7. Play the downloaded copy locally.

Observed result in this pass: NOT_VERIFIED. Automated API tests verify upload metadata and download behavior using representative MP3 bytes. The client UI currently has no `tags` field, so supplying tags through the desktop upload form is not covered.

### Playlist behavior

1. Download at least three tracks.
2. Create a playlist.
3. Add all three tracks.
4. Attempt to add the same track twice and record whether it is ignored or reported.
5. Move one track up and one track down.
6. Remove one track.
7. Restart the client.
8. Confirm the playlist order persists.
9. Play the playlist and verify manual order.
10. Test next and previous.
11. Test shuffle.
12. Test loop off, loop one, and loop all.
13. Create an empty playlist and click **Play playlist**.
14. Create a one-track playlist and test next, previous, loop one, and loop all.
15. Delete a local audio file referenced by a playlist and confirm playback does not crash.

Observed result in this pass: NOT_VERIFIED for live GUI/audio behavior. SQLite persistence and controller order logic are covered by automated tests.

### User experience

1. Start the client with the server stopped and confirm the catalog error is visible.
2. Start the server and refresh/search the catalog.
3. Verify invalid actions have clear disabled states or visible messages:
   * download with no selected catalog row;
   * play with no selected downloaded row;
   * add to playlist with no selected downloaded row;
   * play empty playlist.
4. Resize the window to a small laptop size and confirm key controls remain accessible.
5. While downloading and uploading, interact with tabs, search fields, and playback controls to confirm the UI remains responsive.

Observed result in this pass: NOT_VERIFIED. Code inspection shows several invalid actions are handled by message boxes rather than disabled buttons.
