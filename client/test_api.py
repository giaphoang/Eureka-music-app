from __future__ import annotations

from pathlib import Path

import pytest

from eureka_client import api as api_module
from eureka_client.api import MusicAPI, UserVisibleAPIError
from eureka_client.workers.task import Task


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


class FakeUploadClient:
    def __init__(self, response) -> None:
        self.response = response

    def __enter__(self) -> "FakeUploadClient":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def post(self, *_: object, **__: object):
        return self.response


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


def test_duplicate_upload_raises_user_visible_message(tmp_path: Path, monkeypatch) -> None:
    audio = tmp_path / "song.mp3"
    audio.write_bytes(b"ID3duplicate")
    response = api_module.httpx.Response(
        409,
        json={"detail": "This audio file already exists"},
        request=api_module.httpx.Request("POST", "http://server/api/v1/tracks"),
    )
    monkeypatch.setattr(
        api_module.httpx,
        "Client",
        lambda *_, **__: FakeUploadClient(response),
    )

    with pytest.raises(UserVisibleAPIError, match="This audio file already exists"):
        MusicAPI("http://server").upload_track(
            audio,
            {"title": "Song", "artist": "Artist"},
        )


def test_task_emits_user_visible_api_errors_without_traceback() -> None:
    messages: list[str] = []
    task = Task(lambda: (_ for _ in ()).throw(UserVisibleAPIError("This audio file already exists")))
    task.signals.error.connect(messages.append)

    task.run()

    assert messages == ["This audio file already exists"]
