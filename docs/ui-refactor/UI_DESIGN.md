# UI Design

## Design Goals

- Replace the tab-oriented client with a desktop music shell.
- Preserve the existing API, SQLite, playback, worker, upload, download, and playlist behavior.
- Keep large collections in Qt model/view widgets.
- Keep startup under 10 seconds with 8,000 local tracks.
- Avoid remote artwork, expensive effects, and one-widget-per-track layouts.

## Reference Direction

The redesign is Spotify-inspired, not a Spotify copy:

- Spotify Desktop: persistent sidebar, dark hierarchy, bottom player, compact track lists.
- Feishin: optional queue panel and dense self-hosted player layout.
- KDE Elisa: local-library clarity and desktop-native organization.

No Spotify logos, proprietary fonts, proprietary artwork, or third-party music-service assets are included.

## Layout

```text
Sidebar | Top bar + stacked page area | Optional queue panel
------------------------------------------------------------
Persistent bottom player bar
```

Implemented regions:

- `Sidebar`: Browse, Downloads, Playlists, Upload, and playlist shortcuts.
- `TopBar`: page title, disabled back/forward placeholders, explicit search box.
- `QStackedWidget`: Browse, Downloads, Playlists, Upload.
- `QueuePanel`: hidden by default, toggleable from the player bar.
- `PlayerBar`: persistent now-playing metadata, transport controls, seek, shuffle, loop, stop, queue toggle.

## Color Tokens

```text
Application background: #000000
Main surface:           #121212
Elevated surface:       #181818
Hover surface:          #242424
Selection surface:      #303030
Text primary:           #FFFFFF
Text secondary:         #B3B3B3
Text disabled:          #727272
Primary action:         #1ED760
Action hover:           #3BE477
Divider:                #2A2A2A
Focus:                  #FFFFFF
```

The theme is centralized in:

```text
client/eureka_client/ui/theme.py
client/eureka_client/ui/resources/theme.qss
```

## Typography

- Brand and page titles use heavier labels.
- Secondary metadata uses muted text.
- Track lists stay compact and table-oriented.
- Buttons use text for page-level actions and icons for transport/navigation controls.

## Component States

- Loading: `LoadingState`
- Empty: `EmptyState`
- Success/error/info: `Toast`
- Disabled pagination and navigation controls where action is invalid
- Queue hidden by default

## Accessibility

Implemented:

- Accessible names on icon-only buttons.
- Tooltips on icon-only buttons.
- Visible focus styling in QSS.
- Keyboard shortcuts:
  - `Ctrl+F`: focus search
  - `Ctrl+L`: Downloads
  - `Ctrl+U`: Upload
  - `Ctrl+Right`: next
  - `Ctrl+Left`: previous
  - `Space`: play/pause unless focus is in a text input
  - `Escape`: hide queue or transient toast

## Large-Scale Behavior

- Track collections use `QTableView` and `QAbstractTableModel`.
- The queue uses the same model/view table component.
- Pages are created once during `MainWindow` initialization and reused.
- No remote artwork is loaded.
- Placeholder artwork is deterministic text based on track metadata.
- SVG icons are local files.
