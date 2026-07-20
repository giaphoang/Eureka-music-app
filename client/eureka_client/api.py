import mimetypes
import os
from pathlib import Path
from typing import Callable

import httpx

from eureka_client.config import API_BASE_URL, DOWNLOAD_DIR


class UserVisibleAPIError(RuntimeError):
    user_visible = True


def raise_for_api_status(response: httpx.Response) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = None
        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail = payload.get("detail")
        except ValueError:
            pass
        if detail:
            raise UserVisibleAPIError(str(detail)) from exc
        raise


class MusicAPI:
    def __init__(self, base_url: str = API_BASE_URL) -> None:
        self.base_url = base_url.rstrip("/")

    def list_tracks(self, query: str = "", offset: int = 0, limit: int = 200) -> dict:
        with httpx.Client(base_url=self.base_url, timeout=20) as client:
            response = client.get(
                "/api/v1/tracks",
                params={"q": query or None, "offset": offset, "limit": limit},
            )
            response.raise_for_status()
            return response.json()

    def generate_playlist(self, prompt: str, size: int) -> dict:
        with httpx.Client(base_url=self.base_url, timeout=httpx.Timeout(180.0, connect=5.0)) as client:
            response = client.post(
                "/api/v1/recommendations/playlists",
                json={"prompt": prompt, "size": size},
            )
            raise_for_api_status(response)
            payload = response.json()
        for track in payload.get("tracks", []):
            track["id"] = track["track_id"]
        return payload

    def download_track(
        self,
        track: dict,
        progress: Callable[[int], None] | None = None,
    ) -> Path:
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        suffix = Path(track.get("original_name") or "track.mp3").suffix or ".mp3"
        final_path = DOWNLOAD_DIR / f"{int(track['id']):06d}{suffix.lower()}"
        temp_path = final_path.with_suffix(final_path.suffix + ".part")
        url = track["download_url"]
        if not url.startswith("http"):
            url = self.base_url + url

        try:
            with httpx.stream("GET", url, timeout=60) as response:
                response.raise_for_status()
                total = int(response.headers.get("content-length", "0") or 0)
                written = 0
                with temp_path.open("wb") as out:
                    for chunk in response.iter_bytes(1024 * 256):
                        out.write(chunk)
                        written += len(chunk)
                        if progress and total:
                            progress(min(100, int(written * 100 / total)))
                    out.flush()
                    os.fsync(out.fileno())
            os.replace(temp_path, final_path)
            return final_path
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

    def upload_track(self, file_path: Path, metadata: dict) -> dict:
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        with file_path.open("rb") as audio, httpx.Client(base_url=self.base_url, timeout=60) as client:
            response = client.post(
                "/api/v1/tracks",
                data={key: value for key, value in metadata.items() if value not in (None, "")},
                files={"audio": (file_path.name, audio, content_type)},
            )
            raise_for_api_status(response)
            return response.json()
