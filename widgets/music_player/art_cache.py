"""
Asynchronous Album Artwork Fetcher & Cache.
Loads cover art from memory byte streams or fetches high-definition artwork
from online metadata providers (iTunes / Deezer Search API) in the background.
"""

import hashlib
import json
import logging
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional, Dict

from PySide6.QtCore import QObject, Signal, QThread, QByteArray
from PySide6.QtGui import QPixmap, QImage

logger = logging.getLogger(__name__)


class ArtFetchWorker(QThread):
    """Background worker to download artwork without blocking Qt UI thread."""
    art_loaded = Signal(str, QPixmap)  # (cache_key, pixmap)

    def __init__(self, query: str, cache_key: str, parent=None):
        super().__init__(parent)
        self.query = query
        self.cache_key = cache_key

    def run(self):
        try:
            url = f"https://itunes.apple.com/search?term={urllib.parse.quote(self.query)}&entity=song&limit=1"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("resultCount", 0) > 0:
                    art_url = data["results"][0].get("artworkUrl100", "").replace("100x100bb", "600x600bb")
                    if art_url:
                        img_req = urllib.request.Request(art_url, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(img_req, timeout=5) as img_resp:
                            img_data = img_resp.read()
                            img = QImage()
                            if img.loadFromData(img_data):
                                pixmap = QPixmap.fromImage(img)
                                self.art_loaded.emit(self.cache_key, pixmap)
                                return
        except Exception as e:
            logger.debug(f"Could not fetch online artwork for '{self.query}': {e}")


class ArtworkManager(QObject):
    """Manages in-memory pixmap cache and dispatches background downloads."""

    artwork_ready = Signal(str, QPixmap)  # (track_id, pixmap)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cache: Dict[str, QPixmap] = {}
        self._active_workers: Dict[str, ArtFetchWorker] = {}

    def get_cached_artwork(self, key: str) -> Optional[QPixmap]:
        return self._cache.get(key)

    def load_from_bytes(self, key: str, image_bytes: bytes) -> Optional[QPixmap]:
        """Loads and caches cover art directly from SMTC thumbnail stream bytes."""
        try:
            img = QImage()
            if img.loadFromData(image_bytes):
                pixmap = QPixmap.fromImage(img)
                self._cache[key] = pixmap
                return pixmap
        except Exception as e:
            logger.warning(f"Error loading image from bytes: {e}")
        return None

    def fetch_online_artwork(self, title: str, artist: str) -> Optional[QPixmap]:
        """Requests high-res artwork online if not already cached or fetching."""
        clean_title = title.strip()
        clean_artist = artist.strip()
        if not clean_title:
            return None

        query = f"{clean_title} {clean_artist}".strip()
        key = hashlib.md5(query.lower().encode("utf-8")).hexdigest()

        if key in self._cache:
            return self._cache[key]

        if key in self._active_workers:
            return None  # Already in flight

        worker = ArtFetchWorker(query=query, cache_key=key, parent=self)
        worker.art_loaded.connect(self._on_worker_art_loaded)
        worker.finished.connect(lambda: self._active_workers.pop(key, None))
        self._active_workers[key] = worker
        worker.start()
        return None

    def _on_worker_art_loaded(self, key: str, pixmap: QPixmap):
        self._cache[key] = pixmap
        self.artwork_ready.emit(key, pixmap)
