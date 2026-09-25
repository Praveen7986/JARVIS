"""
Audio playback engine for the Music Player widget using PySide6.QtMultimedia.
Supports local audio loading (.mp3, .wav, .m4a, .flac), playlists, seeking, and volume.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Optional

from PySide6.QtCore import QObject, Signal, QUrl, QTime
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

logger = logging.getLogger(__name__)

DEFAULT_PLAYLIST = [
    {
        "title": "Midnight City Lofi",
        "artist": "Aether Beats",
        "album": "Deep Focus Session",
        "file_path": "",
        "duration_ms": 214000,
    },
    {
        "title": "Cyber Synth Horizon",
        "artist": "Neon Wave",
        "album": "Night Drive Vol. 1",
        "file_path": "",
        "duration_ms": 185000,
    },
    {
        "title": "Cosmic Rain & Coffee",
        "artist": "Chillhop Studio",
        "album": "Rainy Days",
        "file_path": "",
        "duration_ms": 242000,
    }
]


class AudioPlayerEngine(QObject):
    """Manages audio playback, playlist queues, and media status."""

    track_changed = Signal(dict)
    state_changed = Signal(bool)  # True = playing, False = paused/stopped
    position_changed = Signal(int, int)  # (current_ms, duration_ms)
    volume_changed = Signal(float)  # 0.0 to 1.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)

        self.audio_output.setVolume(0.8)

        self.playlist: List[Dict] = list(DEFAULT_PLAYLIST)
        self.current_index = 0
        self.is_simulated = True  # When using virtual/demo tracks

        self._wire_signals()

    def _wire_signals(self):
        self.player.positionChanged.connect(self._on_player_position_changed)
        self.player.durationChanged.connect(self._on_player_duration_changed)
        self.player.playbackStateChanged.connect(self._on_player_state_changed)

    def current_track(self) -> Optional[Dict]:
        if 0 <= self.current_index < len(self.playlist):
            return self.playlist[self.current_index]
        return None

    def load_files(self, file_paths: List[str]):
        """Adds real audio files to the playlist and plays the first added track."""
        valid_paths = [p for p in file_paths if os.path.exists(p)]
        if not valid_paths:
            return

        new_tracks = []
        for p in valid_paths:
            path_obj = Path(p)
            new_tracks.append({
                "title": path_obj.stem,
                "artist": "Local Audio",
                "album": path_obj.parent.name,
                "file_path": str(path_obj.resolve()),
                "duration_ms": 0,
            })

        self.playlist = new_tracks + self.playlist
        self.current_index = 0
        self.play_track_at(0)

    def play_track_at(self, index: int):
        if not (0 <= index < len(self.playlist)):
            return

        self.current_index = index
        track = self.playlist[index]
        file_path = track.get("file_path", "")

        if file_path and os.path.exists(file_path):
            self.is_simulated = False
            self.player.setSource(QUrl.fromLocalFile(file_path))
            self.player.play()
        else:
            self.is_simulated = True
            # Virtual play state for bundled tracks
            self.player.stop()
            self.state_changed.emit(True)

        self.track_changed.emit(track)

    def toggle_play(self):
        track = self.current_track()
        if not track:
            return

        file_path = track.get("file_path", "")
        if file_path and os.path.exists(file_path):
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
            else:
                self.player.play()
        else:
            # Toggle virtual simulation state
            is_currently_playing = self.is_playing()
            self.state_changed.emit(not is_currently_playing)

    def play(self):
        track = self.current_track()
        if not track:
            return
        file_path = track.get("file_path", "")
        if file_path and os.path.exists(file_path):
            self.player.play()
        else:
            self.state_changed.emit(True)

    def pause(self):
        self.player.pause()
        self.state_changed.emit(False)

    def next_track(self):
        if not self.playlist:
            return
        next_idx = (self.current_index + 1) % len(self.playlist)
        self.play_track_at(next_idx)

    def previous_track(self):
        if not self.playlist:
            return
        prev_idx = (self.current_index - 1 + len(self.playlist)) % len(self.playlist)
        self.play_track_at(prev_idx)

    def set_position(self, position_ms: int):
        if not self.is_simulated:
            self.player.setPosition(position_ms)
        else:
            duration = self.get_duration()
            self.position_changed.emit(position_ms, duration)

    def set_volume(self, volume_float: float):
        vol = max(0.0, min(1.0, volume_float))
        self.audio_output.setVolume(vol)
        self.volume_changed.emit(vol)

    def get_volume(self) -> float:
        return self.audio_output.volume()

    def is_playing(self) -> bool:
        if not self.is_simulated:
            return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        return True

    def get_duration(self) -> int:
        if not self.is_simulated:
            return self.player.duration()
        track = self.current_track()
        return track.get("duration_ms", 180000) if track else 180000

    def _on_player_position_changed(self, pos_ms: int):
        dur_ms = self.player.duration()
        self.position_changed.emit(pos_ms, dur_ms)

    def _on_player_duration_changed(self, dur_ms: int):
        pos_ms = self.player.position()
        self.position_changed.emit(pos_ms, dur_ms)

    def _on_player_state_changed(self, state):
        is_p = state == QMediaPlayer.PlaybackState.PlayingState
        self.state_changed.emit(is_p)

    @staticmethod
    def format_time(ms: int) -> str:
        """Converts milliseconds into MM:SS format."""
        total_seconds = max(0, ms // 1000)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
