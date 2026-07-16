# Component Map

| Old widget / responsibility | New page/component | Preserved handler / behavior | Preserved dependency |
| --- | --- | --- | --- |
| `QTabWidget` shell | `Sidebar` + `QStackedWidget` | `MainWindow.show_page()` | Qt navigation state |
| Server catalog tab | `BrowsePage` | `refresh_catalog`, pagination, `download_selected` | `MusicAPI`, `Task` |
| Catalog search row | `TopBar` | `search_catalog` | `MusicAPI.list_tracks` |
| Downloaded tab | `DownloadsPage` | `refresh_local`, `play_local_selected`, `add_local_to_playlist` | `ClientDB`, `PlaybackController` |
| Playlist tab left list | `Sidebar` playlist list | `show_playlist`, `refresh_playlists` | `ClientDB` |
| Playlist tab track table | `PlaylistPage` | create, play, move, remove | `ClientDB`, `PlaybackController` |
| Upload tab | `UploadPage` | choose file, upload selected | `MusicAPI.upload_track`, `Task` |
| Inline player bar in `MainWindow` | `PlayerBar` | play/pause, stop, previous, next, seek, shuffle, loop | `PlaybackController` |
| No queue panel | `QueuePanel` | reflects current playback queue, double-click plays row | `PlaybackController` remains source of truth |
| Repeated table class in `main_window.py` | `TrackTable`, `TrackTableModel` | model/view rendering, selected row/track helpers | Qt model/view |
| Modal/status success feedback | `Toast` | download/upload/playlist feedback | MainWindow orchestration |
| Ad hoc empty/loading text | `EmptyState`, `LoadingState` | browse/download/playlist states | Page presentation only |

## Ownership

`MainWindow` still owns:

- `MusicAPI`
- `ClientDB`
- `PlaybackController`
- `QThreadPool`
- Navigation state
- Current playback queue

Pages and components emit Qt signals for user intent. They do not perform HTTP or SQLite business logic directly.
