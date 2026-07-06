from __future__ import annotations

from pathlib import Path

import pytest

from eureka_client import api as api_module
from eureka_client.api import MusicAPI


class FakeStream:
    def __init__(self, chunks: list[bytes], fail_after_first: bool = False) -> None:
        self.chunks = chunks
        self.fail_after_first = fail_after_first
        self.headers = {"content-length": str(sum(len(chunk) for chunk in chunks))}

    def __enter__(self) -> "FakeStream":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_bytes(self, _: int):
        for index, chunk in enumerate(self.chunks):
            yield chunk
            if self.fail_after_first and index == 0:
                raise RuntimeError("network interrupted")


def test_download_track_writes_file_and_progress(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(api_module, "DOWNLOAD_DIR", tmp_path)
    monkeypatch.setattr(
        api_module.httpx,
        "stream",
        lambda *_, **__: FakeStream([b"ID3", b"audio-data"]),
    )
    progress: list[int] = []

    path = MusicAPI("http://server").download_track(
        {"id": 7, "original_name": "track.mp3", "download_url": "/audio/7"},
        progress.append,
    )

    assert path == tmp_path / "000007.mp3"
    assert path.read_bytes() == b"ID3audio-data"
    assert path.stat().st_size > 0
    assert progress[-1] == 100
    assert list(tmp_path.glob("*.part")) == []


def test_interrupted_download_does_not_leave_complete_or_part_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(api_module, "DOWNLOAD_DIR", tmp_path)
    monkeypatch.setattr(
        api_module.httpx,
        "stream",
        lambda *_, **__: FakeStream([b"partial", b"ignored"], fail_after_first=True),
    )

    with pytest.raises(RuntimeError, match="network interrupted"):
        MusicAPI("http://server").download_track(
            {"id": 8, "original_name": "track.mp3", "download_url": "/audio/8"},
        )

    assert not (tmp_path / "000008.mp3").exists()
    assert list(tmp_path.glob("*.part")) == []


def test_duplicate_download_reuses_final_path_safely(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(api_module, "DOWNLOAD_DIR", tmp_path)
    monkeypatch.setattr(
        api_module.httpx,
        "stream",
        lambda *_, **__: FakeStream([b"ID3same-audio"]),
    )
    api = MusicAPI("http://server")
    track = {"id": 9, "original_name": "track.mp3", "download_url": "/audio/9"}

    first = api.download_track(track)
    second = api.download_track(track)

    assert first == second == tmp_path / "000009.mp3"
    assert second.read_bytes() == b"ID3same-audio"
    assert second.stat().st_size > 0
    assert list(tmp_path.glob("*.part")) == []
